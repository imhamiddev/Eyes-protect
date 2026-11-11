//! Win32 implementation of [`Platform`]. Compiled on Windows only.

use std::ffi::c_void;
use std::os::windows::ffi::OsStrExt;
use std::path::Path;
use std::ptr::{null, null_mut};

use windows_sys::Win32::Foundation::{CloseHandle, HWND, LPARAM, RECT};
use windows_sys::Win32::Graphics::Gdi::{
    CreateDCW, DeleteDC, EnumDisplayMonitors, GetDC, GetMonitorInfoW, ReleaseDC, HDC,
    HMONITOR, MONITORINFOEXW,
};
use windows_sys::Win32::UI::ColorSystem::SetDeviceGammaRamp;
use windows_sys::Win32::Media::Audio::{PlaySoundW, SND_ASYNC, SND_FILENAME, SND_NODEFAULT};
use windows_sys::Win32::System::Registry::{
    RegCloseKey, RegDeleteValueW, RegOpenKeyExW, RegQueryValueExW, RegSetValueExW, HKEY, HKEY_CURRENT_USER,
    KEY_QUERY_VALUE, KEY_SET_VALUE, REG_DWORD, REG_SZ,
};
use windows_sys::Win32::System::SystemInformation::GetTickCount;
use windows_sys::Win32::System::Threading::{CreateMutexW, OpenProcess, QueryFullProcessImageNameW};
use windows_sys::Win32::UI::Input::KeyboardAndMouse::{GetLastInputInfo, LASTINPUTINFO};
use windows_sys::Win32::UI::Shell::SHQueryUserNotificationState;
use windows_sys::Win32::UI::WindowsAndMessaging::{
    GetForegroundWindow, GetWindowTextW, GetWindowThreadProcessId, SendMessageTimeoutW, HWND_BROADCAST,
    SMTO_ABORTIFHUNG, WM_SETTINGCHANGE,
};

use super::{Monitor, Platform};
use crate::common::colortemp::Ramp;
use crate::features::smartpause::Foreground;

const RUN_KEY: &str = r"Software\Microsoft\Windows\CurrentVersion\Run";
const PERSONALIZE_KEY: &str = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize";
const PROCESS_QUERY_LIMITED_INFORMATION: u32 = 0x1000;

fn wide(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(std::iter::once(0)).collect()
}

fn wide_path(p: &Path) -> Vec<u16> {
    p.as_os_str().encode_wide().chain(std::iter::once(0)).collect()
}

fn from_wide(buf: &[u16]) -> String {
    let end = buf.iter().position(|c| *c == 0).unwrap_or(buf.len());
    String::from_utf16_lossy(&buf[..end])
}

/// Open a key under HKEY_CURRENT_USER and run `f` on it.
fn with_key<T>(subkey: &str, access: u32, f: impl FnOnce(HKEY) -> Option<T>) -> Option<T> {
    let mut key: HKEY = null_mut();
    let name = wide(subkey);
    // SAFETY: `name` is NUL-terminated and `key` is a valid out pointer.
    if unsafe { RegOpenKeyExW(HKEY_CURRENT_USER, name.as_ptr(), 0, access, &mut key) } != 0 {
        return None;
    }
    let result = f(key);
    // SAFETY: `key` was opened above.
    unsafe { RegCloseKey(key) };
    result
}

fn set_dword(key: HKEY, name: &str, value: u32) -> bool {
    let name = wide(name);
    // SAFETY: the data pointer references a live u32 of the stated size.
    unsafe { RegSetValueExW(key, name.as_ptr(), 0, REG_DWORD, (&value as *const u32).cast(), 4) == 0 }
}

fn query_dword(key: HKEY, name: &str) -> Option<u32> {
    let name = wide(name);
    let (mut value, mut size, mut kind) = (0u32, 4u32, 0u32);
    // SAFETY: all out pointers reference live locals of the right size.
    let status = unsafe {
        RegQueryValueExW(key, name.as_ptr(), null(), &mut kind, (&mut value as *mut u32).cast(), &mut size)
    };
    (status == 0 && kind == REG_DWORD).then_some(value)
}

pub struct WindowsPlatform;

impl Platform for WindowsPlatform {
    fn idle_seconds(&self) -> f64 {
        let mut info = LASTINPUTINFO { cbSize: std::mem::size_of::<LASTINPUTINFO>() as u32, dwTime: 0 };
        // SAFETY: `info` is initialised with its size as the API requires.
        if unsafe { GetLastInputInfo(&mut info) } == 0 {
            return 0.0;
        }
        // SAFETY: no arguments.
        let now = unsafe { GetTickCount() };
        f64::from(now.wrapping_sub(info.dwTime)) / 1000.0
    }

    fn set_gamma_ramp(&self, ramp: &Ramp) -> bool {
        // SAFETY: the screen DC is released on every path; the ramp is 3x256 u16 as required.
        unsafe {
            let hdc = GetDC(null_mut());
            if hdc.is_null() {
                return false;
            }
            let ok = SetDeviceGammaRamp(hdc, ramp.as_ptr().cast::<c_void>()) != 0;
            ReleaseDC(null_mut(), hdc);
            ok
        }
    }

    fn set_monitor_gamma_ramp(&self, device: &str, ramp: &Ramp) -> bool {
        let (driver, dev) = (wide("DISPLAY"), wide(device));
        // SAFETY: strings are NUL-terminated; the DC is deleted on every path.
        unsafe {
            let hdc: HDC = CreateDCW(driver.as_ptr(), dev.as_ptr(), null(), null());
            if hdc.is_null() {
                return false;
            }
            let ok = SetDeviceGammaRamp(hdc, ramp.as_ptr().cast::<c_void>()) != 0;
            DeleteDC(hdc);
            ok
        }
    }

    fn list_monitors(&self) -> Vec<Monitor> {
        unsafe extern "system" fn callback(hmon: HMONITOR, _hdc: HDC, _rect: *mut RECT, data: LPARAM) -> i32 {
            // SAFETY: `data` is the `&mut Vec<Monitor>` passed to EnumDisplayMonitors below.
            let found = unsafe { &mut *(data as *mut Vec<Monitor>) };
            let mut info: MONITORINFOEXW = unsafe { std::mem::zeroed() };
            info.monitorInfo.cbSize = std::mem::size_of::<MONITORINFOEXW>() as u32;
            if unsafe { GetMonitorInfoW(hmon, (&mut info as *mut MONITORINFOEXW).cast()) } != 0 {
                let r = info.monitorInfo.rcMonitor;
                found.push(Monitor {
                    device: from_wide(&info.szDevice),
                    x: r.left,
                    y: r.top,
                    width: (r.right - r.left).max(0) as u32,
                    height: (r.bottom - r.top).max(0) as u32,
                    primary: info.monitorInfo.dwFlags & 1 != 0,
                });
            }
            1
        }
        let mut found: Vec<Monitor> = Vec::new();
        // SAFETY: the callback only runs during this call, while `found` is alive.
        unsafe { EnumDisplayMonitors(null_mut(), null(), Some(callback), (&mut found as *mut Vec<Monitor>) as LPARAM) };
        found.sort_by(|a, b| (!a.primary, &a.device).cmp(&(!b.primary, &b.device)));
        found
    }

    fn notification_state(&self) -> Option<i32> {
        let mut state = 0i32;
        // SAFETY: `state` is a valid out pointer.
        let hr = unsafe { SHQueryUserNotificationState(&mut state) };
        (hr == 0).then_some(state)
    }

    fn foreground_info(&self) -> Option<Foreground> {
        // SAFETY: plain Win32 queries with correctly sized local buffers.
        unsafe {
            let hwnd: HWND = GetForegroundWindow();
            if hwnd.is_null() {
                return None;
            }
            let mut pid = 0u32;
            GetWindowThreadProcessId(hwnd, &mut pid);
            let mut title = [0u16; 512];
            let n = GetWindowTextW(hwnd, title.as_mut_ptr(), title.len() as i32).max(0) as usize;
            let mut exe = String::new();
            let handle = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid);
            if !handle.is_null() {
                let mut buf = [0u16; 1024];
                let mut size = buf.len() as u32;
                if QueryFullProcessImageNameW(handle, 0, buf.as_mut_ptr(), &mut size) != 0 {
                    let full = from_wide(&buf[..size as usize]).replace('\\', "/");
                    exe = full.rsplit('/').next().unwrap_or("").to_lowercase();
                }
                CloseHandle(handle);
            }
            Some(Foreground { pid, exe, title: String::from_utf16_lossy(&title[..n]) })
        }
    }

    fn play_sound_file(&self, path: &Path) -> bool {
        let p = wide_path(path);
        // SAFETY: `p` is NUL-terminated and outlives the (asynchronous, file-based) call start.
        unsafe { PlaySoundW(p.as_ptr(), null_mut(), SND_FILENAME | SND_ASYNC | SND_NODEFAULT) != 0 }
    }

    fn set_autostart(&self, enabled: bool, command: &str) -> bool {
        with_key(RUN_KEY, KEY_SET_VALUE, |key| {
            let name = wide("EyeCare");
            if enabled {
                let data = wide(command);
                // SAFETY: `data` is a NUL-terminated UTF-16 string; the size is in bytes.
                let status = unsafe { RegSetValueExW(key, name.as_ptr(), 0, REG_SZ, data.as_ptr().cast(), (data.len() * 2) as u32) };
                (status == 0).then_some(())
            } else {
                // A missing value is fine: the app simply was not registered.
                // SAFETY: `name` is NUL-terminated.
                unsafe { RegDeleteValueW(key, name.as_ptr()) };
                Some(())
            }
        })
        .is_some()
    }

    fn system_uses_light_theme(&self) -> bool {
        with_key(PERSONALIZE_KEY, KEY_QUERY_VALUE, |key| query_dword(key, "AppsUseLightTheme")).is_some_and(|v| v != 0)
    }

    fn set_system_light_theme(&self, light: bool) -> bool {
        let value = u32::from(light);
        let ok = with_key(PERSONALIZE_KEY, KEY_SET_VALUE, |key| {
            (set_dword(key, "AppsUseLightTheme", value) && set_dword(key, "SystemUsesLightTheme", value)).then_some(())
        })
        .is_some();
        if ok {
            let topic = wide("ImmersiveColorSet");
            // SAFETY: broadcast with a NUL-terminated string that outlives the call.
            unsafe {
                SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, topic.as_ptr() as LPARAM, SMTO_ABORTIFHUNG, 100, null_mut());
            }
        }
        ok
    }
}

/// Create a named mutex so the installer can detect a running app. The handle is kept for
/// the lifetime of the process.
pub fn create_single_instance_mutex(name: &str) -> bool {
    let n = wide(name);
    // SAFETY: `n` is NUL-terminated; the handle is intentionally leaked.
    unsafe { !CreateMutexW(null(), 0, n.as_ptr()).is_null() }
}
