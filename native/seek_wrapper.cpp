#include <memory>
#include <string>
#include <vector>
#include <cstring>

#include <opencv2/core.hpp>

#include "SeekThermal.h"
#include "SeekThermalPro.h"

namespace {

struct SeekHandle {
    std::unique_ptr<LibSeek::SeekThermal> compact;
    std::unique_ptr<LibSeek::SeekThermalPro> pro;
    LibSeek::SeekCam* camera{nullptr};
    cv::Mat frame;
    int width{0};
    int height{0};
};

enum SeekCameraType {
    SEEK_CAMERA_COMPACT = 0,
    SEEK_CAMERA_PRO = 1,
};

} // namespace

extern "C" {

SeekHandle* seek_open(int camera_type, const char* ffc_path) {
    std::string ffc = ffc_path ? std::string(ffc_path) : std::string();
    auto handle = new SeekHandle();

    try {
        if (camera_type == SEEK_CAMERA_PRO) {
            handle->pro = std::make_unique<LibSeek::SeekThermalPro>(ffc);
            handle->camera = handle->pro.get();
        } else {
            handle->compact = std::make_unique<LibSeek::SeekThermal>(ffc);
            handle->camera = handle->compact.get();
        }
    } catch (...) {
        delete handle;
        return nullptr;
    }

    if (!handle->camera || !handle->camera->open()) {
        delete handle;
        return nullptr;
    }

    if (!handle->camera->read(handle->frame)) {
        handle->camera->close();
        delete handle;
        return nullptr;
    }

    handle->width = handle->frame.cols;
    handle->height = handle->frame.rows;
    return handle;
}

void seek_close(SeekHandle* handle) {
    if (!handle) {
        return;
    }
    if (handle->camera) {
        handle->camera->close();
        handle->camera = nullptr;
    }
    delete handle;
}

int seek_get_dimensions(SeekHandle* handle, int* width, int* height) {
    if (!handle || !width || !height) {
        return 0;
    }
    *width = handle->width;
    *height = handle->height;
    return 1;
}

int seek_read_frame(SeekHandle* handle, uint16_t* out_buffer, int capacity) {
    if (!handle || !out_buffer || capacity <= 0) {
        return -1;
    }

    if (!handle->camera->read(handle->frame)) {
        return -2;
    }

    const auto total_pixels = handle->frame.rows * handle->frame.cols;
    if (capacity < total_pixels) {
        return -3;
    }

    std::memcpy(out_buffer, handle->frame.ptr<uint16_t>(), total_pixels * sizeof(uint16_t));
    return static_cast<int>(total_pixels);
}

} // extern "C"

