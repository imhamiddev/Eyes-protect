//! Eye Care - a quiet companion that protects your eyes.
//!
//! This crate is the Rust rewrite of the Python application that lives in `../eyecare`.
//! Platform-independent logic lives in [`common`] and [`features`]; everything that touches
//! Windows is isolated behind the `platform` module so the logic can be unit-tested anywhere.

pub const APP_NAME: &str = "Eye Care";
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

pub mod common;
pub mod features;

pub mod platform;
