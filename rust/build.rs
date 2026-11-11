//! Embeds the application icon into the Windows executable.

fn main() {
    println!("cargo:rerun-if-changed=eyecare.rc");
    println!("cargo:rerun-if-changed=assets/eyecare.ico");
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows") {
        // A missing resource compiler must not break the build; the exe simply has no icon then.
        if let Err(e) = embed_resource::compile("eyecare.rc", embed_resource::NONE).manifest_optional() {
            println!("cargo:warning=could not embed the icon: {e}");
        }
    }
}
