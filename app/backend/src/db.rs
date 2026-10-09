use std::sync::Arc;

use std::sync::atomic::{AtomicI64, Ordering};

use lbug::{Connection, Database, PreparedStatement, SystemConfig, Value};
use sha1::{Digest, Sha1};

pub struct AppState {
    db: Arc<Database>,
    label_counter: Arc<AtomicI64>,
}

impl Clone for AppState {
    fn clone(&self) -> Self {
        Self {
            db: Arc::clone(&self.db),
            label_counter: Arc::clone(&self.label_counter),
        }
    }
}

fn sha1_short(input: &str) -> String {
    let mut hasher = Sha1::new();
    hasher.update(input.as_bytes());
    let hash = hasher.finalize();
    hash.iter().take(6).map(|b| format!("{b:02x}")).collect()
}

fn create_schema(conn: &Connection) {
    let _ = conn.query(
        "CREATE NODE TABLE IF NOT EXISTS Artist (
            artist_id STRING,
            name STRING,
            PRIMARY KEY (artist_id)
        )",
    );

    let _ = conn.query(
        "CREATE NODE TABLE IF NOT EXISTS Album (
            album_id STRING,
            title STRING,
            year STRING,
            artist_id STRING,
            PRIMARY KEY (album_id)
        )",
    );

    let _ = conn.query(
        "CREATE NODE TABLE IF NOT EXISTS Track (
            track_id STRING,
            title STRING,
            artist STRING,
            album STRING,
            genre STRING,
            section_start DOUBLE,
            section_end DOUBLE,
            PRIMARY KEY (track_id)
        )",
    );

    let _ = conn.query("ALTER TABLE Track ADD IF NOT EXISTS genre STRING");

    let _ = conn.query(
        "CREATE NODE TABLE IF NOT EXISTS Label (
            label_id INT64,
            track_id STRING,
            color_hex STRING,
            mode STRING,
            time_to_select_ms INT64,
            created_at STRING,
            PRIMARY KEY (label_id)
        )",
    );

    let _ = conn.query("CREATE REL TABLE IF NOT EXISTS PERFORMS (FROM Artist TO Track)");
    let _ = conn
        .query("CREATE REL TABLE IF NOT EXISTS CONTAINS (FROM Album TO Track, track_number INT32)");
    let _ = conn.query("CREATE REL TABLE IF NOT EXISTS Labeled (FROM Label TO Track)");
}

impl AppState {
    pub fn new(path: &str) -> Result<Self, Box<dyn std::error::Error>> {
        if path != ":memory:" {
            let parent = std::path::Path::new(path)
                .parent()
                .unwrap_or(std::path::Path::new("."));
            std::fs::create_dir_all(parent)?;
        }

        let db = Database::new(path, SystemConfig::default())?;
        let conn = Connection::new(&db)?;
        create_schema(&conn);
        let seed = max_label_id(&conn);
        drop(conn);

        Ok(Self {
            db: Arc::new(db),
            label_counter: Arc::new(AtomicI64::new(seed + 1)),
        })
    }

    pub fn seed_from_manifest(
        &self,
        manifest_path: &str,
    ) -> Result<u32, Box<dyn std::error::Error>> {
        let content = match std::fs::read_to_string(manifest_path) {
            Ok(c) => c,
            Err(_) => {
                tracing::warn!("manifest not found at {manifest_path}, skipping seed");
                return Ok(0);
            }
        };

        let conn = Connection::new(&self.db)?;

        let mut upsert_artist: PreparedStatement =
            conn.prepare("MERGE (a:Artist {artist_id: $artist_id}) ON CREATE SET a.name = $name")?;
        let mut upsert_album: PreparedStatement = conn.prepare(
            "MERGE (al:Album {album_id: $album_id}) \
             ON CREATE SET al.title = $title, al.year = $year, al.artist_id = $artist_id",
        )?;
        let mut upsert_track: PreparedStatement = conn.prepare(
            "MERGE (t:Track {track_id: $track_id}) \
             ON CREATE SET t.title = $title, t.artist = $artist, t.album = $album, \
                           t.genre = $genre, t.section_start = $ss, t.section_end = $se",
        )?;
        let mut create_performs: PreparedStatement = conn.prepare(
            "MATCH (a:Artist {artist_id: $artist_id}), (t:Track {track_id: $track_id}) \
             MERGE (a)-[:PERFORMS]->(t)",
        )?;
        let mut create_contains: PreparedStatement = conn.prepare(
            "MATCH (al:Album {album_id: $album_id}), (t:Track {track_id: $track_id}) \
             MERGE (al)-[:CONTAINS {track_number: $tn}]->(t)",
        )?;

        let mut count = 0u32;
        for line in content.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            let track: serde_json::Value = serde_json::from_str(line)?;

            let artist = track["artist"].as_str().unwrap_or("").to_string();
            let album = track["album"].as_str().unwrap_or("").to_string();
            let track_id = track["track_id"].as_str().unwrap_or("").to_string();
            let title = track["title"].as_str().unwrap_or("").to_string();
            let genre = track["genre"].as_str().unwrap_or("").to_string();
            let year = track["year"].as_str().unwrap_or("").to_string();
            let track_number = track["track_number"].as_i64().unwrap_or(0) as i32;
            let section_start = track["section_start"].as_f64().unwrap_or(0.0);
            let section_end = track["section_end"].as_f64().unwrap_or(0.0);

            let artist_id = sha1_short(&artist);
            let album_id = sha1_short(&format!("{artist}|{album}"));

            conn.execute(
                &mut upsert_artist,
                vec![
                    ("artist_id", artist_id.clone().into()),
                    ("name", artist.clone().into()),
                ],
            )?;

            conn.execute(
                &mut upsert_album,
                vec![
                    ("album_id", album_id.clone().into()),
                    ("title", album.clone().into()),
                    ("year", year.clone().into()),
                    ("artist_id", artist_id.clone().into()),
                ],
            )?;

            conn.execute(
                &mut upsert_track,
                vec![
                    ("track_id", track_id.clone().into()),
                    ("title", title.clone().into()),
                    ("artist", artist.clone().into()),
                    ("album", album.clone().into()),
                    ("genre", genre.into()),
                    ("ss", Value::Double(section_start)),
                    ("se", Value::Double(section_end)),
                ],
            )?;

            conn.execute(
                &mut create_performs,
                vec![
                    ("artist_id", artist_id.clone().into()),
                    ("track_id", track_id.clone().into()),
                ],
            )?;

            conn.execute(
                &mut create_contains,
                vec![
                    ("album_id", album_id.clone().into()),
                    ("track_id", track_id.clone().into()),
                    ("tn", Value::Int32(track_number)),
                ],
            )?;

            count += 1;
        }

        Ok(count)
    }

    pub fn next_label_id(&self) -> i64 {
        self.label_counter.fetch_add(1, Ordering::Relaxed)
    }

    pub fn query(&self, query: &str) -> Result<Vec<Vec<Value>>, lbug::Error> {
        let conn = Connection::new(&self.db)?;
        let mut result = conn.query(query)?;
        let mut rows = Vec::new();
        while let Some(row) = result.next() {
            rows.push(row);
        }
        Ok(rows)
    }

    pub fn execute(&self, query: &str) -> Result<(), lbug::Error> {
        let conn = Connection::new(&self.db)?;
        conn.query(query)?;
        Ok(())
    }
}

pub fn max_label_id(conn: &Connection) -> i64 {
    match conn.query("MATCH (l:Label) RETURN l.label_id") {
        Ok(mut result) => {
            let mut max_id = 0i64;
            while let Some(row) = result.next() {
                if let Some(value) = get_int(&row, 0) {
                    if value > max_id {
                        max_id = value;
                    }
                }
            }
            max_id
        }
        Err(_) => 0,
    }
}

pub fn get_string(row: &[Value], idx: usize) -> Option<String> {
    match &row.get(idx)? {
        Value::String(s) => Some(s.clone()),
        _ => None,
    }
}

pub fn get_int(row: &[Value], idx: usize) -> Option<i64> {
    match &row.get(idx)? {
        Value::Int64(i) => Some(*i),
        _ => None,
    }
}

pub fn get_double(row: &[Value], idx: usize) -> Option<f64> {
    match &row.get(idx)? {
        Value::Double(d) => Some(*d),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture_manifest() -> String {
        [
            r#"{"track_id": "t001", "title": "Song One", "artist": "Test Artist", "album": "Test Album", "genre": "Rock", "year": "1970", "track_number": 1, "section_start": 10.0, "section_end": 20.0}"#,
            r#"{"track_id": "t002", "title": "Song Two", "artist": "Test Artist", "album": "Test Album", "genre": "Rock", "year": "1970", "track_number": 2, "section_start": 30.0, "section_end": 42.5}"#,
            r#"{"track_id": "t003", "title": "Song Three", "artist": "O'Brien Band", "album": "What's Going On", "genre": "Soul", "year": "1971", "track_number": 1, "section_start": 5.0, "section_end": 15.0}"#,
        ]
        .join("\n")
    }

    #[test]
    fn test_seed_from_manifest() {
        let tmp = std::env::temp_dir().join(format!("lbug_test_{}", std::process::id()));
        std::fs::create_dir_all(&tmp).unwrap();
        let db_path = tmp.join("test.lbdb");
        let manifest_path = tmp.join("tracks.jsonl");

        let manifest = fixture_manifest();
        std::fs::write(&manifest_path, &manifest).unwrap();

        let state = AppState::new(db_path.to_str().unwrap()).unwrap();
        let count = state
            .seed_from_manifest(manifest_path.to_str().unwrap())
            .unwrap();
        assert_eq!(count, 3);

        let artists = state.query("MATCH (a:Artist) RETURN count(a)").unwrap();
        assert_eq!(get_int(&artists[0], 0).unwrap(), 2);

        let albums = state.query("MATCH (al:Album) RETURN count(al)").unwrap();
        assert_eq!(get_int(&albums[0], 0).unwrap(), 2);

        let tracks = state.query("MATCH (t:Track) RETURN count(t)").unwrap();
        assert_eq!(get_int(&tracks[0], 0).unwrap(), 3);

        let performs = state
            .query("MATCH (a:Artist)-[:PERFORMS]->(t:Track) RETURN count(a)")
            .unwrap();
        assert_eq!(get_int(&performs[0], 0).unwrap(), 3);

        let contains = state
            .query("MATCH (al:Album)-[:CONTAINS]->(t:Track) RETURN count(al)")
            .unwrap();
        assert_eq!(get_int(&contains[0], 0).unwrap(), 3);

        let expected_artist_id = sha1_short("Test Artist");
        let artist_row = state
            .query(&format!(
                "MATCH (a:Artist) WHERE a.artist_id = '{expected_artist_id}' RETURN a.name"
            ))
            .unwrap();
        assert_eq!(get_string(&artist_row[0], 0).unwrap(), "Test Artist");

        let apostrophe_album = state
            .query("MATCH (al:Album) WHERE al.title CONTAINS 'Going' RETURN al.title, al.year")
            .unwrap();
        assert_eq!(
            get_string(&apostrophe_album[0], 0).unwrap(),
            "What's Going On"
        );
        assert_eq!(get_string(&apostrophe_album[0], 1).unwrap(), "1971");

        let count2 = state
            .seed_from_manifest(manifest_path.to_str().unwrap())
            .unwrap();
        assert_eq!(count2, 3);

        let tracks2 = state.query("MATCH (t:Track) RETURN count(t)").unwrap();
        assert_eq!(get_int(&tracks2[0], 0).unwrap(), 3);

        drop(state);
        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn test_sha1_short() {
        let hash = sha1_short("The Beatles");
        assert_eq!(hash.len(), 12);
        assert!(hash.chars().all(|c| c.is_ascii_hexdigit()));

        assert_eq!(sha1_short("The Beatles"), sha1_short("The Beatles"));
        assert_ne!(sha1_short("The Beatles"), sha1_short("Beatles"));
    }

    #[test]
    fn test_list_tracks_paging() {
        let tmp = std::env::temp_dir().join(format!("lbug_paging_{}", std::process::id()));
        std::fs::create_dir_all(&tmp).unwrap();
        let db_path = tmp.join("pg.lbdb");
        let manifest_path = tmp.join("tracks.jsonl");
        std::fs::write(&manifest_path, &fixture_manifest()).unwrap();

        let state = AppState::new(db_path.to_str().unwrap()).unwrap();
        state
            .seed_from_manifest(manifest_path.to_str().unwrap())
            .unwrap();

        let all = state.query("MATCH (t:Track) RETURN t.track_id").unwrap();
        assert_eq!(all.len(), 3);

        let page = state
            .query("MATCH (t:Track) RETURN t.track_id SKIP 1 LIMIT 1")
            .unwrap();
        assert_eq!(page.len(), 1);
        assert_eq!(get_string(&page[0], 0).unwrap(), "t002");

        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn test_label_counter_seeding() {
        let tmp = std::env::temp_dir().join(format!("lbug_counter_{}", std::process::id()));
        std::fs::create_dir_all(&tmp).unwrap();
        let db_path = tmp.join("ct.lbdb");

        let state = AppState::new(db_path.to_str().unwrap()).unwrap();
        assert_eq!(state.next_label_id(), 1);
        assert_eq!(state.next_label_id(), 2);

        state.execute("CREATE (l:Label {label_id: 42, track_id: 'x', color_hex: '#fff', mode: 'instrumental', time_to_select_ms: 5, created_at: '0'})").unwrap();

        let reloaded = AppState::new(db_path.to_str().unwrap()).unwrap();
        assert_eq!(reloaded.next_label_id(), 43);

        let before = state.next_label_id();
        let after_clone = state.clone().next_label_id();
        assert_eq!(after_clone, before + 1);

        let _ = std::fs::remove_dir_all(&tmp);
    }
}
