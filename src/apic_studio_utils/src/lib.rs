extern crate exr;
extern crate image;

use exr::prelude as exrs;
use exr::prelude::*;
use image::codecs::hdr::HdrDecoder;
use image::imageops::resize;
use image::imageops::FilterType;
use image::io::Reader as ImageReader;
use image::{DynamicImage, ImageBuffer, Rgb, Rgba};
use pyo3::prelude::*;
use std::fs::File;
use std::io::BufReader;
use xcap;

#[pyfunction]
fn sdr_to_jpg(input: &str, output: &str, resize_width: u32) -> PyResult<()> {
    if input.ends_with(".hdr") {
        return hdr_to_jpg(input, output, resize_width);
    } else if input.ends_with(".exr") {
        return exr_to_jpg(input, output, resize_width);
    } else {
        unreachable!("Unsupported file format");
    }
}

#[pyfunction]
fn exr_to_jpg(input: &str, output: &str, resize_width: u32) -> PyResult<()> {
    let reader = exrs::read()
        .no_deep_data()
        .largest_resolution_level()
        .rgba_channels(
            |resolution, _channels: &RgbaChannels| -> image::RgbaImage {
                image::ImageBuffer::new(resolution.width() as u32, resolution.height() as u32)
            },
            // set each pixel in the png buffer from the exr file
            |png_pixels, position, (r, g, b, a): (f32, f32, f32, f32)| {
                // TODO implicit argument types!
                png_pixels.put_pixel(
                    position.x() as u32,
                    position.y() as u32,
                    image::Rgba([tone_map(r), tone_map(g), tone_map(b), (a * 255.0) as u8]),
                );
            },
        )
        .first_valid_layer()
        .all_attributes();

    let image: Image<Layer<SpecificChannels<image::RgbaImage, RgbaChannels>>> = reader
        .from_file(input)
        .expect("run the `1_write_rgba` example to generate the required file");

    let jpg_buffer = &image.layer_data.channel_data.pixels;
    let resize_factor = jpg_buffer.width() as f32 / resize_width as f32;
    let resize_height = jpg_buffer.height() as f32 / resize_factor;
    let w = jpg_buffer.width();
    let h = jpg_buffer.height();

    let resized = resize(
        jpg_buffer,
        resize_width,
        resize_height as u32,
        FilterType::Lanczos3,
    );
    resized.save(output).unwrap();

    return Ok(());
}

#[pyfunction]
fn hdr_to_jpg(input: &str, output: &str, resize_width: u32) -> PyResult<()> {
    let file = File::open(input).expect("Unable to open file");
    let buf_reader = BufReader::new(file);

    let hdr_decoder = HdrDecoder::new(buf_reader).unwrap();
    let metadata = hdr_decoder.metadata();

    let hdr_data = hdr_decoder.read_image_hdr().unwrap();

    let hdr_data_flat: Vec<f32> = hdr_data
        .iter()
        .flat_map(|&Rgb([r, g, b])| vec![r, g, b])
        .collect();

    let hdr_image: ImageBuffer<Rgb<f32>, _> =
        ImageBuffer::from_raw(metadata.width as u32, metadata.height as u32, hdr_data_flat)
            .unwrap();

    let (width, height) = hdr_image.dimensions();
    let mut img = ImageBuffer::<Rgb<u8>, _>::new(width, height);

    let resize_factor = width / resize_width;
    let resize_height = height / resize_factor;

    for (x, y, pixel) in img.enumerate_pixels_mut() {
        let hdr_pixel = hdr_image.get_pixel(x, y);
        *pixel = Rgb([
            tone_map(hdr_pixel[0]),
            tone_map(hdr_pixel[1]),
            tone_map(hdr_pixel[2]),
        ]);
    }
    let ldr_image = DynamicImage::ImageRgb8(img);
    let ldr_image_resized = ldr_image.resize(resize_width, resize_height, FilterType::Lanczos3);

    ldr_image_resized.save(output).unwrap();

    return Ok(());
}

#[pyfunction]
fn screenshot(
    output: &str,
    x: u32,
    y: u32,
    width: u32,
    height: u32,
    resize_width: u32,
) -> PyResult<()> {
    use std::cmp::{max, min};
    use std::path::PathBuf;

    // Work in signed space so negative monitor origins are handled.
    let shot_x = x as i32;
    let shot_y = y as i32;
    let shot_w = width as i32;
    let shot_h = height as i32;

    let resize_factor = width as f32 / resize_width as f32;
    let resize_height = (height as f32 / resize_factor).round() as u32;

    let monitors = xcap::Monitor::all()
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("monitor list: {e}")))?;

    // Helper: overlap area between two rects
    let overlap_area =
        |ax: i32, ay: i32, aw: i32, ah: i32, bx: i32, by: i32, bw: i32, bh: i32| -> i32 {
            let rx = max(ax, bx);
            let ry = max(ay, by);
            let rr = min(ax + aw, bx + bw);
            let rb = min(ay + ah, by + bh);
            let w = (rr - rx).max(0);
            let h = (rb - ry).max(0);
            w * h
        };

    // Build the shot rect once
    let sx = shot_x;
    let sy = shot_y;
    let sw = shot_w;
    let sh = shot_h;

    // Pick monitor with the largest overlap with the requested region
    let mut best = None::<(xcap::Monitor, i32)>;
    for m in monitors.into_iter() {
        let mx = m.x().unwrap_or(0);
        let my = m.y().unwrap_or(0);
        let mw = m.width().unwrap_or(0) as i32;
        let mh = m.height().unwrap_or(0) as i32;

        let area = overlap_area(mx, my, mw, mh, sx, sy, sw, sh);
        if area > 0 {
            match &best {
                None => best = Some((m, area)),
                Some((_, best_area)) if area > *best_area => best = Some((m, area)),
                _ => {}
            }
        }
    }

    let monitor = match best {
        Some((m, _)) => m,
        None => {
            // Fallback: try the monitor that contains the top-left point, if any
            let monitors2 = xcap::Monitor::all().map_err(|e| {
                pyo3::exceptions::PyRuntimeError::new_err(format!("monitor list: {e}"))
            })?;
            let m = monitors2
                .into_iter()
                .find(|m| {
                    let mx = m.x().unwrap_or(0);
                    let my = m.y().unwrap_or(0);
                    let mw = m.width().unwrap_or(0) as i32;
                    let mh = m.height().unwrap_or(0) as i32;
                    (sx >= mx) && (sy >= my) && (sx < mx + mw) && (sy < my + mh)
                })
                .ok_or_else(|| {
                    pyo3::exceptions::PyValueError::new_err(
                        "No monitor overlaps the requested region",
                    )
                })?;
            m
        }
    };

    // Compute region relative to the chosen monitor’s origin.
    let mx = monitor.x().unwrap_or(0);
    let my = monitor.y().unwrap_or(0);
    let rel_x = (shot_x - mx).max(0) as u32;
    let rel_y = (shot_y - my).max(0) as u32;

    // Clamp capture size to the monitor bounds so we don't go OOB.
    let mw = monitor.width().unwrap_or(0);
    let mh = monitor.height().unwrap_or(0);
    let max_w = mw.saturating_sub(rel_x);
    let max_h = mh.saturating_sub(rel_y);
    let cap_w = width.min(max_w);
    let cap_h = height.min(max_h);

    // If your input is in logical pixels, convert here:
    // let scale = monitor.scale().unwrap_or(1.0); // if xcap exposes it
    // let rel_x = ((shot_x - mx) as f32 * scale).round() as u32;
    // let rel_y = ((shot_y - my) as f32 * scale).round() as u32;
    // let cap_w = (width as f32 * scale).round() as u32;
    // let cap_h = (height as f32 * scale).round() as u32;

    let image = monitor
        .capture_region(rel_x, rel_y, cap_w, cap_h)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("capture_region: {e}")))?;

    let ldr_image = xcap::image::DynamicImage::ImageRgba8(image);
    let resized_img = ldr_image.resize(
        resize_width,
        resize_height,
        xcap::image::imageops::FilterType::Lanczos3,
    );

    let path = PathBuf::from(output);
    resized_img
        .save(path)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("save: {e}")))?;

    Ok(())
}

#[pyfunction]
fn apply_srgb_gamma(file: &str) -> PyResult<()> {
    // Open + decode with the image crate (re-exported via xcap::image)
    let dynimg = ImageReader::open(file)
        .expect("Failed to open image")
        .decode()
        .expect("Failed to decode image");

    // Work in RGBA8 so we can preserve alpha
    let mut rgba = dynimg.to_rgba8();

    // Build a 256-entry LUT for gamma = 1/2.2
    let mut lut = [0u8; 256];
    let inv_gamma = 1.0f32 / 2.2f32;
    for (i, v) in lut.iter_mut().enumerate() {
        let f = (i as f32) / 255.0;
        let corrected = f.powf(inv_gamma);
        *v = (corrected * 255.0).round().clamp(0.0, 255.0) as u8;
    }

    // Apply to RGB channels, keep alpha untouched
    for px in rgba.pixels_mut() {
        let [r, g, b, a] = px.0;
        *px = Rgba([lut[r as usize], lut[g as usize], lut[b as usize], a]);
    }

    // Save back to the same path (format inferred from extension)
    DynamicImage::ImageRgba8(rgba)
        .save(file)
        .expect("failed to save image");
    Ok(())
}

#[pymodule]
fn rust_thumbnails(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(exr_to_jpg, m)?)?;
    m.add_function(wrap_pyfunction!(hdr_to_jpg, m)?)?;
    m.add_function(wrap_pyfunction!(sdr_to_jpg, m)?)?;
    m.add_function(wrap_pyfunction!(screenshot, m)?)?;
    m.add_function(wrap_pyfunction!(apply_srgb_gamma, m)?)?;
    Ok(())
}

fn tone_map(linear: f32) -> u8 {
    let exposure_factor = 4.0;
    let exposed_linear = linear * exposure_factor;
    let mapped = exposed_linear / (1.0 + exposed_linear);
    (mapped * 255.0).clamp(0.0, 255.0) as u8
}
