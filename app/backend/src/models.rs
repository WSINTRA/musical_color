use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize)]
pub struct Track {
    pub track_id: String,
    pub title: String,
    pub artist: String,
    pub album: String,
    pub section_start: f64,
    pub section_end: f64,
}

#[derive(Debug, Deserialize)]
pub struct LabelInput {
    pub track_id: String,
    pub color_hex: String,
    pub mode: String,
    pub time_to_select_ms: i64,
}

#[derive(Debug, Serialize)]
pub struct LabelResponse {
    pub label_id: i64,
    pub status: String,
}
