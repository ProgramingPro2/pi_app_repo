import numpy as np

from pi_app.app.modes import (
    FlatFieldCalibrationMode,
    LiveHighlightMode,
    ModeHooks,
    ModeResult,
    ModeState,
    PaletteMode,
    SettingsMode,
)
from pi_app.app.processing import TemperatureModel


def make_state():
    return ModeState(palette_names=["GRAY", "HOT"])


def test_live_mode_threshold_updates():
    state = make_state()
    mode = LiveHighlightMode()
    model = TemperatureModel()
    frame = np.full((4, 4), 2000, dtype=np.uint16)
    result = mode.update(frame, model.to_celsius(frame), state, model)
    assert isinstance(result, ModeResult)
    assert result.highlight_color == state.highlight_color()

    banner = mode.on_button_up(state)
    assert "Threshold" in banner
    consumed, message = mode.on_mode_button(state)
    assert consumed is True
    assert "Highlight" in message


def test_palette_mode_cycles():
    state = make_state()
    mode = PaletteMode()
    model = TemperatureModel()
    frame = np.zeros((2, 2), dtype=np.uint16)
    mode.update(frame, model.to_celsius(frame), state, model)

    name_before = state.palette_name
    mode.on_button_up(state)
    assert state.palette_name != name_before
    mode.on_button_down(state)
    assert state.palette_name == name_before


def test_flat_field_capture(tmp_path):
    saved = {}

    def save_ffc(frame):
        saved["frame"] = frame.copy()
        return str(tmp_path / "ffc.png")

    def reload(path):
        saved["reload"] = path

    state = make_state()
    hooks = ModeHooks(save_ffc=save_ffc, reload_camera=reload)
    mode = FlatFieldCalibrationMode(hooks, frames_to_average=2)
    model = TemperatureModel()

    mode.on_enter(state)
    mode.on_button_up(state)
    frame1 = np.ones((2, 2), dtype=np.uint16)
    frame2 = np.full((2, 2), 3, dtype=np.uint16)

    mode.update(frame1, model.to_celsius(frame1), state, model)
    result = mode.update(frame2, model.to_celsius(frame2), state, model)

    assert "frame" in saved
    assert np.all(saved["frame"] == 2)
    assert result.banner is not None
    assert saved["reload"] == str(tmp_path / "ffc.png")
    assert state.ff_last_saved == str(tmp_path / "ffc.png")


def test_settings_mode_menu():
    state = make_state()
    mode = SettingsMode()
    model = TemperatureModel()
    frame = np.zeros((2, 2), dtype=np.uint16)

    mode.update(frame, model.to_celsius(frame), state, model)
    mode.on_button_up(state)
    consumed, message = mode.on_mode_button(state)
    assert consumed
    assert "Units" in (message or "")
    assert state.temperature_unit == "F"
    mode.on_button_down(state)
    consumed, message = mode.on_mode_button(state)
    assert consumed


def test_reset_threshold_respects_unit():
    state = make_state()
    state.temperature_unit = "F"
    state.default_threshold_f = 95.0
    state.threshold_c = state.convert_display_to_c(80.0)
    mode = SettingsMode()
    state.settings_index = 3  # Reset Threshold entry
    consumed, message = mode.on_mode_button(state)
    assert consumed
    assert abs(state.threshold_display - 95.0) < 1e-6


def test_live_mode_threshold_units():
    state = make_state()
    state.temperature_unit = "F"
    mode = LiveHighlightMode()
    prev_c = state.threshold_c
    banner = mode.on_button_up(state)
    assert "°F" in banner
    expected_c = prev_c + (1.0 - 0.0) * 5.0 / 9.0
    assert abs(state.threshold_c - expected_c) < 1e-6

