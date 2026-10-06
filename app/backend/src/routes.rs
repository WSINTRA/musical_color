use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    routing::get,
    Json,
    Router,
};
use tower_http::cors::{Any, CorsLayer};
use tower_http::services::ServeDir;

use std::collections::HashSet;

use crate::db::{get_double, get_string, AppState};
use crate::models::{LabelInput, LabelResponse, Track};

pub fn build(state: AppState) -> Router {
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    Router::new()
        .route("/api/tracks", get(list_tracks))
        .route("/api/tracks/{track_id}", get(get_track))
        .route("/api/labels", axum::routing::post(create_label))
        .route_service("/clips", ServeDir::new("data/clips"))
        .layer(cors)
        .with_state(state)
}

const DEFAULT_PAGE_LIMIT: u32 = 25;
const MAX_PAGE_LIMIT: u32 = 100;

#[derive(Debug, serde::Deserialize)]
struct SeenPage {
    #[serde(default)]
    ids: Vec<String>,
    #[serde(default)]
    offset: u32,
    #[serde(default)]
    limit: u32,
}

async fn list_tracks(
    State(state): State<AppState>,
    Query(page): Query<SeenPage>,
) -> Result<Json<Vec<Track>>, StatusCode> {
    let limit =
        if page.limit == 0 {
            DEFAULT_PAGE_LIMIT
        } else {
            page.limit.min(MAX_PAGE_LIMIT)
        };
    let offset = page.offset;

    let rows = state
        .query(&format!(
            "MATCH (t:Track) RETURN t.track_id, t.title, t.artist, t.album, t.section_start, t.section_end SKIP {offset} LIMIT {limit}",
        ))
        .map_err(|e| {
            tracing::error!("query failed: {e}");
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let seen: HashSet<String> = page.ids.into_iter().collect();
    let tracks: Vec<Track> = rows
        .into_iter()
        .filter_map(|row| {
            let track_id = get_string(&row, 0)?;
            if seen.contains(&track_id) {
                return None;
            }
            Some(Track {
                title: get_string(&row, 1).unwrap_or_default(),
                artist: get_string(&row, 2).unwrap_or_default(),
                album: get_string(&row, 3).unwrap_or_default(),
                section_start: get_double(&row, 4).unwrap_or(0.0),
                section_end: get_double(&row, 5).unwrap_or(0.0),
                track_id,
            })
        })
        .collect();

    Ok(Json(tracks))
}

async fn get_track(
    State(state): State<AppState>,
    Path(track_id): Path<String>,
) -> Result<Json<Track>, StatusCode> {
    let safe_id = track_id.replace('\'', "''");
    let rows = state
        .query(&format!(
            "MATCH (t:Track) WHERE t.track_id = '{safe_id}' RETURN t.track_id, t.title, t.artist, t.album, t.section_start, t.section_end"
        ))
        .map_err(|e| {
            tracing::error!("query failed: {e}");
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let row = match rows.into_iter().next() {
        Some(r) => r,
        None => return Err(StatusCode::NOT_FOUND),
    };

    Ok(Json(Track {
        track_id,
        title: get_string(&row, 1).unwrap_or_default(),
        artist: get_string(&row, 2).unwrap_or_default(),
        album: get_string(&row, 3).unwrap_or_default(),
        section_start: get_double(&row, 4).unwrap_or(0.0),
        section_end: get_double(&row, 5).unwrap_or(0.0),
    }))
}

async fn create_label(
    State(state): State<AppState>,
    Json(input): Json<LabelInput>,
) -> Result<Json<LabelResponse>, StatusCode> {
    let label_id = state.next_label_id();

    let now = unix_timestamp();
    let safe_track = input.track_id.replace('\'', "''");
    let safe_color = input.color_hex.replace('\'', "''");
    let safe_mode = input.mode.replace('\'', "''");

    state
        .execute(&format!(
            "CREATE (l:Label {{label_id: {label_id}, track_id: '{safe_track}', color_hex: '{safe_color}', mode: '{safe_mode}', time_to_select_ms: {}, created_at: '{now}'}})",
            input.time_to_select_ms
        ))
        .map_err(|e| {
            tracing::error!("failed to create label: {e}");
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    state
        .execute(&format!(
            "MATCH (l:Label {{label_id: {label_id}}}), (t:Track {{track_id: '{safe_track}'}}) CREATE (l)-[:Labeled]->(t)"
        ))
        .map_err(|e| {
            tracing::error!("failed to create relationship: {e}");
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    Ok(Json(LabelResponse {
        label_id,
        status: "created".into(),
    }))
}

fn unix_timestamp() -> String {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs()
        .to_string()
}
