use std::sync::Arc;

use lbug::{Connection, Database, SystemConfig, Value};

pub struct AppState {
    db: Arc<Database>,
}

impl Clone for AppState {
    fn clone(&self) -> Self {
        Self {
            db: Arc::clone(&self.db),
        }
    }
}

impl AppState {
    pub fn new(path: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let parent = std::path::Path::new(path)
            .parent()
            .unwrap_or(std::path::Path::new("."));
        std::fs::create_dir_all(parent)?;

        let db = Database::new(path, SystemConfig::default())?;
        let conn = Connection::new(&db)?;

        let _ = conn.query(
            "CREATE NODE TABLE IF NOT EXISTS Track (
                track_id STRING,
                title STRING,
                artist STRING,
                album STRING,
                section_start DOUBLE,
                section_end DOUBLE,
                PRIMARY KEY (track_id)
            )",
        );

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

        let _ = conn.query("CREATE REL TABLE IF NOT EXISTS Labeled (FROM Label TO Track)");

        drop(conn);

        Ok(Self { db: Arc::new(db) })
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
