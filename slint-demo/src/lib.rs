slint::include_modules!();

#[no_mangle]
fn android_main(app: slint::android::AndroidApp) {
    slint::android::init(app).unwrap();
    App::new().unwrap().run().unwrap();
}
