import json
import warnings
from pathlib import Path

import napari
from napari_toolkit.containers import setup_vgroupbox
from napari_toolkit.containers.boxlayout import hstack
from napari_toolkit.utils import get_value, set_value
from napari_toolkit.widgets import (
    setup_label,
    setup_lineedit,
    setup_pushbutton,
    setup_spinbox,
)
from qtpy.QtCore import QEvent, QObject, Signal
from qtpy.QtWidgets import (
    QFileDialog,
    QVBoxLayout,
    QWidget,
)


class ResizeWatcher(QObject):
    resize_event = Signal()

    def __init__(self):
        super().__init__()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            self.resize_event.emit()
        return super().eventFilter(obj, event)


class CameraControlWidget(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer"):
        super().__init__()
        self._viewer = viewer
        self.file_ending = ".ncam"

        self.build_gui()

        self.window_resize_watcher = ResizeWatcher()
        self.canvas_resize_watcher = ResizeWatcher()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            self._viewer.window._qt_window.installEventFilter(self.window_resize_watcher)
            viewer.window._qt_viewer.canvas.native.installEventFilter(self.canvas_resize_watcher)

        self.connect_viewer()
        self.connect_gui()
        self.on_viewer_changed()

    def build_gui(self):
        main_layout = QVBoxLayout()
        # --- 1. Dimensions --- #
        _container, _layout = setup_vgroupbox(main_layout, "Dimensions")

        label = setup_label(None, "Displayed:")
        self.dims_ndisplay = setup_spinbox(None, 2, 3, 1, 2)
        hstack(_layout, [label, self.dims_ndisplay])

        label = setup_label(None, "Order:")
        self.dims_order = setup_lineedit(None, "")
        hstack(_layout, [label, self.dims_order])

        _container, _layout = setup_vgroupbox(main_layout, "Current Step")

        label_x = setup_label(None, "X:")
        label_y = setup_label(None, "Y:")
        label_z = setup_label(None, "Z:")
        #
        label_x.setFixedWidth(20)
        label_y.setFixedWidth(20)
        label_z.setFixedWidth(20)

        self.current_z = setup_lineedit(None, "")
        self.current_y = setup_lineedit(None, "")
        self.current_x = setup_lineedit(None, "")

        self.current_x.setFixedWidth(50)
        self.current_y.setFixedWidth(50)
        self.current_z.setFixedWidth(50)

        hstack(_layout, [label_x, self.current_x, label_y, self.current_y, label_z, self.current_z])

        # --- 2. Camera --- #
        # --- 2.1. Zoom --- #
        _container, _layout = setup_vgroupbox(main_layout, "Camera Zoom")
        self.camera_zoom = setup_lineedit(_layout, "")

        # --- 2.2. Center --- #
        _container, _layout = setup_vgroupbox(main_layout, "Camera Center")

        label_x = setup_label(None, "X:")
        label_y = setup_label(None, "Y:")
        label_z = setup_label(None, "Z:")
        label_x.setFixedWidth(20)
        label_y.setFixedWidth(20)
        label_z.setFixedWidth(20)

        self.camera_center_z = setup_lineedit(None, "")
        self.camera_center_y = setup_lineedit(None, "")
        self.camera_center_x = setup_lineedit(None, "")

        hstack(
            _layout,
            [
                label_x,
                self.camera_center_x,
            ],
        )
        hstack(
            _layout,
            [
                label_y,
                self.camera_center_y,
            ],
        )
        hstack(
            _layout,
            [
                label_z,
                self.camera_center_z,
            ],
        )

        # --- 2.2. Angle --- #
        _container, _layout = setup_vgroupbox(main_layout, "Camera Angle")

        label_x = setup_label(None, "X:")
        label_y = setup_label(None, "Y:")
        label_z = setup_label(None, "Z:")
        label_x.setFixedWidth(20)
        label_y.setFixedWidth(20)
        label_z.setFixedWidth(20)

        self.camera_angle_z = setup_lineedit(None, "")
        self.camera_angle_y = setup_lineedit(None, "")
        self.camera_angle_x = setup_lineedit(None, "")

        hstack(
            _layout,
            [
                label_x,
                self.camera_angle_x,
            ],
        )
        hstack(
            _layout,
            [
                label_y,
                self.camera_angle_y,
            ],
        )
        hstack(
            _layout,
            [
                label_z,
                self.camera_angle_z,
            ],
        )

        # --- 3 Window --- #
        # --- 3.1. Window --- #
        _container, _layout = setup_vgroupbox(main_layout, "Window")

        label_w = setup_label(None, "Width:")
        label_h = setup_label(None, "Height:")
        label_w.setFixedWidth(50)
        label_h.setFixedWidth(60)
        self.window_width = setup_lineedit(None, "")
        self.window_height = setup_lineedit(None, "")
        self.window_width.setFixedWidth(55)
        self.window_height.setFixedWidth(55)

        hstack(_layout, [label_w, self.window_width, label_h, self.window_height])

        # --- 3.2. Canvas --- #
        _container, _layout = setup_vgroupbox(main_layout, "Canvas")
        label_w = setup_label(None, "Width:")
        label_h = setup_label(None, "Height:")
        label_w.setFixedWidth(50)
        label_h.setFixedWidth(60)
        self.canvas_width = setup_lineedit(None, "")
        self.canvas_height = setup_lineedit(None, "")
        self.canvas_width.setFixedWidth(55)
        self.canvas_height.setFixedWidth(55)

        hstack(_layout, [label_w, self.canvas_width, label_h, self.canvas_height])

        # --- 4. IO --- #
        _container, _layout = setup_vgroupbox(main_layout, "")
        self.load_btn = setup_pushbutton(None, "Load", function=self.load)
        self.save_btn = setup_pushbutton(None, "Save", function=self.save)
        _ = hstack(_layout, [self.load_btn, self.save_btn])

        self.setLayout(main_layout)

    def connect_gui(self):
        # Dimension
        self.dims_ndisplay.valueChanged.connect(self.on_gui_changed)
        self.dims_order.returnPressed.connect(self.on_gui_changed)
        self.current_z.returnPressed.connect(self.on_gui_changed)
        self.current_y.returnPressed.connect(self.on_gui_changed)
        self.current_x.returnPressed.connect(self.on_gui_changed)
        # Camera
        self.camera_zoom.returnPressed.connect(self.on_gui_changed)
        self.camera_center_z.returnPressed.connect(self.on_gui_changed)
        self.camera_center_y.returnPressed.connect(self.on_gui_changed)
        self.camera_center_x.returnPressed.connect(self.on_gui_changed)
        self.camera_angle_z.returnPressed.connect(self.on_gui_changed)
        self.camera_angle_y.returnPressed.connect(self.on_gui_changed)
        self.camera_angle_x.returnPressed.connect(self.on_gui_changed)
        # Window
        self.window_width.returnPressed.connect(self.on_gui_changed)
        self.window_height.returnPressed.connect(self.on_gui_changed)
        self.canvas_width.returnPressed.connect(self.on_gui_changed)
        self.canvas_height.returnPressed.connect(self.on_gui_changed)

    def disconnect_gui(self):
        # Dimension
        self.dims_ndisplay.valueChanged.disconnect(self.on_gui_changed)
        self.dims_order.returnPressed.disconnect(self.on_gui_changed)
        self.current_z.returnPressed.disconnect(self.on_gui_changed)
        self.current_y.returnPressed.disconnect(self.on_gui_changed)
        self.current_x.returnPressed.disconnect(self.on_gui_changed)
        # Camera
        self.camera_zoom.returnPressed.disconnect(self.on_gui_changed)
        self.camera_center_z.returnPressed.disconnect(self.on_gui_changed)
        self.camera_center_y.returnPressed.disconnect(self.on_gui_changed)
        self.camera_center_x.returnPressed.disconnect(self.on_gui_changed)
        self.camera_angle_z.returnPressed.disconnect(self.on_gui_changed)
        self.camera_angle_y.returnPressed.disconnect(self.on_gui_changed)
        self.camera_angle_x.returnPressed.disconnect(self.on_gui_changed)
        # Window
        self.window_width.returnPressed.disconnect(self.on_gui_changed)
        self.window_height.returnPressed.disconnect(self.on_gui_changed)
        self.canvas_width.returnPressed.disconnect(self.on_gui_changed)
        self.canvas_height.returnPressed.disconnect(self.on_gui_changed)

    def connect_viewer(self):
        # Dimension
        self._viewer.dims.events.ndisplay.connect(self.on_viewer_changed)
        self._viewer.dims.events.order.connect(self.on_viewer_changed)
        self._viewer.dims.events.current_step.connect(self.on_viewer_changed)
        # Camera
        self._viewer.camera.events.center.connect(self.on_viewer_changed)
        self._viewer.camera.events.zoom.connect(self.on_viewer_changed)
        self._viewer.camera.events.angles.connect(self.on_viewer_changed)
        # Window
        self.window_resize_watcher.resize_event.connect(self.on_viewer_changed)
        self.canvas_resize_watcher.resize_event.connect(self.on_viewer_changed)

    def disconnect_viewer(self):
        # Dimension
        self._viewer.dims.events.ndisplay.disconnect(self.on_viewer_changed)
        self._viewer.dims.events.ndisplay.disconnect(self.on_viewer_changed)
        self._viewer.dims.events.order.disconnect(self.on_viewer_changed)
        self._viewer.dims.events.current_step.disconnect(self.on_viewer_changed)
        # Camera
        self._viewer.camera.events.center.disconnect(self.on_viewer_changed)
        self._viewer.camera.events.zoom.disconnect(self.on_viewer_changed)
        self._viewer.camera.events.angles.disconnect(self.on_viewer_changed)
        # Window
        self.window_resize_watcher.resize_event.disconnect(self.on_viewer_changed)
        self.canvas_resize_watcher.resize_event.disconnect(self.on_viewer_changed)

    def get_config_from_gui(self):
        config = {}
        config["ndisplay"] = int(get_value(self.dims_ndisplay))
        config["order"] = tuple(int(x) for x in get_value(self.dims_order).split(","))
        config["current_step"] = (
            int(get_value(self.current_z)),
            int(get_value(self.current_y)),
            int(get_value(self.current_x)),
        )
        # Get Camera
        config["camera_zoom"] = float(get_value(self.camera_zoom))
        config["camera_center"] = (
            float(get_value(self.camera_center_z)),
            float(get_value(self.camera_center_y)),
            float(get_value(self.camera_center_x)),
        )
        config["camera_angle"] = (
            float(get_value(self.camera_angle_z)),
            float(get_value(self.camera_angle_y)),
            float(get_value(self.camera_angle_x)),
        )
        # Get Window
        config["window_size"] = (
            int(get_value(self.window_width)),
            int(get_value(self.window_height)),
        )
        config["canvas_size"] = (
            int(get_value(self.canvas_height)),
            int(get_value(self.canvas_width)),
        )
        return config

    def get_config_from_view(self):

        config = {
            "ndisplay": self._viewer.dims.ndisplay,
            "order": self._viewer.dims.order,
            "current_step": self._viewer.dims.current_step,
            "camera_zoom": self._viewer.camera.zoom,
            "camera_center": self._viewer.camera.center,
            "camera_angle": self._viewer.camera.angles,
        }
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            config["window_size"] = self._viewer.window.geometry()[2:]
            config["canvas_size"] = self._viewer._canvas_size
        return config

    def set_config_to_gui(self, config):
        set_value(self.dims_ndisplay, int(config["ndisplay"]))
        set_value(self.dims_order, ", ".join(str(x) for x in config["order"]))
        current_step = config["current_step"]
        if len(current_step) == 2:
            current_step = [0] + list(current_step)
        set_value(self.current_z, str(current_step[0]))
        set_value(self.current_y, str(current_step[1]))
        set_value(self.current_x, str(current_step[2]))

        # Update Camera
        set_value(self.camera_zoom, str(config["camera_zoom"]))
        set_value(self.camera_center_z, str(config["camera_center"][0]))
        set_value(self.camera_center_y, str(config["camera_center"][1]))
        set_value(self.camera_center_x, str(config["camera_center"][2]))
        set_value(self.camera_angle_z, str(config["camera_angle"][0]))
        set_value(self.camera_angle_y, str(config["camera_angle"][1]))
        set_value(self.camera_angle_x, str(config["camera_angle"][2]))

        # Set Cursor position to beginning to handle text overflow
        self.camera_zoom.setCursorPosition(0)
        self.camera_center_z.setCursorPosition(0)
        self.camera_center_y.setCursorPosition(0)
        self.camera_center_x.setCursorPosition(0)
        self.camera_angle_z.setCursorPosition(0)
        self.camera_angle_y.setCursorPosition(0)
        self.camera_angle_x.setCursorPosition(0)

        # Update Window
        set_value(self.window_width, str(config["window_size"][0]))
        set_value(self.window_height, str(config["window_size"][1]))
        set_value(self.canvas_width, str(config["canvas_size"][1]))
        set_value(self.canvas_height, str(config["canvas_size"][0]))

    def set_config_to_view(self, config):
        self._viewer.dims.ndisplay = config["ndisplay"]
        self._viewer.dims.order = config["order"]
        self._viewer.dims.current_step = config["current_step"]

        # Set Camera
        self._viewer.camera.zoom = config["camera_zoom"]
        self._viewer.camera.center = config["camera_center"]
        self._viewer.camera.angles = config["camera_angle"]

        # Set Window
        window_size = config["window_size"]
        self._viewer.window.resize(*window_size)

        # Set Canvas
        # Set Window
        canvas_size = config["canvas_size"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            canvas_size_current = self._viewer._canvas_size
            window_size_current = self._viewer.window.geometry()[2:]

        diff_height = canvas_size_current[0] - canvas_size[0]
        diff_width = canvas_size_current[1] - canvas_size[1]

        window_size_new = (
            window_size_current[0] - diff_width,
            window_size_current[1] - diff_height,
        )

        # Exit fullscreen or maximized mode
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            if (
                self._viewer.window._qt_window.isFullScreen()
                or self._viewer.window._qt_window.isMaximized()
            ):
                self._viewer.window._qt_window.showNormal()

        self._viewer.window.resize(*window_size_new)

    def on_viewer_changed(self):

        config = self.get_config_from_view()
        self.disconnect_gui()
        self.set_config_to_gui(config)
        self.connect_gui()

    def on_gui_changed(self):
        config = self.get_config_from_gui()
        self.disconnect_viewer()
        self.set_config_to_view(config)
        self.connect_viewer()

        self.on_viewer_changed()

    def save(self):

        _dialog = QFileDialog(self)
        _dialog.setDirectory(str(Path.cwd()))
        config_path, _ = _dialog.getSaveFileName(
            self,
            "Select File",
            f"camera_view{self.file_ending}",
            filter=f"*{self.file_ending}",
            options=QFileDialog.DontUseNativeDialog,
        )
        if config_path is not None and config_path.endswith(self.file_ending):
            config_path = Path(config_path)
            config = self.get_config_from_view()

            with Path(config_path).open("w") as f:
                json.dump(config, f, indent=4)
        else:
            print("No Valid File Selected")

    def load(self):

        _dialog = QFileDialog(self)
        _dialog.setDirectory(str(Path.cwd()))
        config_path, _ = _dialog.getOpenFileName(
            self,
            "Select File",
            filter=f"*{self.file_ending}",
            options=QFileDialog.DontUseNativeDialog,
        )
        if config_path is not None and config_path.endswith(self.file_ending):
            with Path(config_path).open("r") as f:
                config = json.load(f)

            self.disconnect_viewer()
            self.set_config_to_view(config)
            self.connect_viewer()

            self.on_viewer_changed()

        else:
            print("No Valid File Selected")
