from __future__ import annotations

import contextlib
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from AppKit import NSRunningApplication  # type: ignore
from Quartz import (  # type: ignore
    CGEventCreateKeyboardEvent,
    CGEventCreateMouseEvent,
    CGEventKeyboardSetUnicodeString,
    CGEventPost,
    CGPointMake,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskShift,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGEventMouseMoved,
    kCGHIDEventTap,
)

from ..errors import ActionExecutionError
from ..models import AXNodeSnapshot, ElementMatch, PressAction, ScrollAction, TypeAction

# PyObjC naming is mildly cursed.
# Depending on the installed framework split, AX symbols may come from
# ApplicationServices or Quartz.
try:
    from ApplicationServices import (  # type: ignore
        AXIsProcessTrustedWithOptions,
        AXUIElementCopyAttributeValue,
        AXUIElementCreateApplication,
        AXUIElementPerformAction,
        AXUIElementSetAttributeValue,
    )
except ImportError:  # pragma: no cover
    from Quartz import (  # type: ignore
        AXIsProcessTrustedWithOptions,
        AXUIElementCopyAttributeValue,
        AXUIElementCreateApplication,
        AXUIElementPerformAction,
        AXUIElementSetAttributeValue,
    )

kAXChildrenAttribute = "AXChildren"
kAXDescriptionAttribute = "AXDescription"
kAXEnabledAttribute = "AXEnabled"
kAXFocusedAttribute = "AXFocused"
kAXFocusedWindowAttribute = "AXFocusedWindow"
kAXMainWindowAttribute = "AXMainWindow"
kAXPositionAttribute = "AXPosition"
kAXPressAction = "AXPress"
kAXRoleAttribute = "AXRole"
kAXSizeAttribute = "AXSize"
kAXSubroleAttribute = "AXSubrole"
kAXTitleAttribute = "AXTitle"
kAXTrustedCheckOptionPrompt = "AXTrustedCheckOptionPrompt"
kAXValueAttribute = "AXValue"
kAXVisibleAttribute = "AXVisible"
kAXWindowsAttribute = "AXWindows"

# Mouse event subtype sometimes exposed as kCGMouseButtonLeft, sometimes raw 0.
try:  # pragma: no cover
    from Quartz import kCGMouseButtonLeft  # type: ignore
except ImportError:  # pragma: no cover
    kCGMouseButtonLeft = 0  # type: ignore[assignment]


@dataclass(slots=True, frozen=True)
class AXBackendConfig:
    prompt_for_access: bool = True
    snapshot_max_depth: int = 8
    snapshot_max_children: int = 200
    action_delay_seconds: float = 0.035
    traversal_delay_seconds: float = 0.0


class AXBackend:
    """
    Real macOS backend for mac-maestro.

    Capabilities:
    - Accessibility permission check
    - App resolution by bundle id
    - AX tree snapshot
    - Semantic click via AXPress with mouse fallback
    - Direct value setting for text fields with keyboard fallback
    - Raw key press via CGEvent

    Constraints:
    - Requires macOS
    - Requires Accessibility permission
    - Requires PyObjC frameworks
    """

    def __init__(self, config: AXBackendConfig | None = None) -> None:
        self.config = config or AXBackendConfig()
        self._element_cache: dict[str, Any] = {}

    # -------------------------------------------------------------------------
    # Public API required by BackendProtocol
    # -------------------------------------------------------------------------

    def snapshot(self, bundle_id: str) -> AXNodeSnapshot:
        self.ensure_accessibility_permissions(prompt=self.config.prompt_for_access)

        app_ref = self._app_ref(bundle_id)
        root = self._best_root_element(app_ref)
        self._element_cache.clear()

        return self._snapshot_element(
            element=root,
            path="root",
            depth=0,
            bundle_id=bundle_id,
        )

    def click(self, match: ElementMatch) -> None:
        element = self._resolve_cached_element(match.element_id)

        if self._try_ax_press(element):
            self._sleep_action_delay()
            return

        point = self._element_center(element)
        self._mouse_left_click(point["x"], point["y"])
        self._sleep_action_delay()

    def double_click(self, match: ElementMatch) -> None:
        element = self._resolve_cached_element(match.element_id)
        point = self._element_center(element)
        self._mouse_left_double_click(point["x"], point["y"])
        self._sleep_action_delay()

    def right_click(self, match: ElementMatch) -> None:
        element = self._resolve_cached_element(match.element_id)
        point = self._element_center(element)
        self._mouse_right_click(point["x"], point["y"])
        self._sleep_action_delay()

    def hover(self, match: ElementMatch) -> None:
        element = self._resolve_cached_element(match.element_id)
        point = self._element_center(element)
        self._mouse_move(point["x"], point["y"])
        self._sleep_action_delay()

    def type_text(self, action: TypeAction, match: ElementMatch | None) -> None:
        target = None if match is None else self._resolve_cached_element(match.element_id)

        # Preferred path: write directly into AXValue when a target exists.
        if target is not None:
            if action.clear_first:
                self._set_attr(target, kAXValueAttribute, "")

            current = self._copy_attr(target, kAXValueAttribute)
            next_value = f"{current or ''}{action.text}" if not action.clear_first else action.text

            if self._set_attr(target, kAXFocusedAttribute, True):
                self._sleep_action_delay()

            if self._set_attr(target, kAXValueAttribute, next_value):
                self._sleep_action_delay()
                return

        # Fallback path: type via keyboard events into the currently focused element.
        if action.clear_first:
            self._send_clear_shortcut()

        self._send_text(action.text)
        self._sleep_action_delay()

    def press(self, action: PressAction) -> None:
        flags = self._modifier_flags(action.modifiers)

        down = CGEventCreateKeyboardEvent(None, action.key_code, True)
        up = CGEventCreateKeyboardEvent(None, action.key_code, False)

        if down is None or up is None:
            raise ActionExecutionError("Failed to create keyboard events.")

        try:
            down.setFlags_(flags)  # PyObjC bridge
            up.setFlags_(flags)
        except AttributeError:
            # Some bridge variants expose CGEventSetFlags instead of setFlags_.
            try:
                from Quartz import CGEventSetFlags  # type: ignore

                CGEventSetFlags(down, flags)
                CGEventSetFlags(up, flags)
            except Exception as exc:  # pragma: no cover
                raise ActionExecutionError(f"Failed to apply modifier flags: {exc}") from exc

        CGEventPost(kCGHIDEventTap, down)
        CGEventPost(kCGHIDEventTap, up)
        self._sleep_action_delay()

    def scroll(self, action: ScrollAction, match: ElementMatch | None) -> None:
        if match is not None:
            element = self._resolve_cached_element(match.element_id)
            point = self._element_center(element)
            self._mouse_move(point["x"], point["y"])
            self._sleep_action_delay()

        try:
            from Quartz import CGEventCreateScrollWheelEvent
        except ImportError:
            CGEventCreateScrollWheelEvent = None

        if CGEventCreateScrollWheelEvent is not None:
            y_amount = 0
            x_amount = 0
            if action.direction == "up":
                y_amount = action.amount
            elif action.direction == "down":
                y_amount = -action.amount
            elif action.direction == "left":
                x_amount = -action.amount
            elif action.direction == "right":
                x_amount = action.amount

            try:
                if y_amount != 0:
                    evt = CGEventCreateScrollWheelEvent(None, 0, 1, y_amount)
                else:
                    evt = CGEventCreateScrollWheelEvent(None, 0, 2, 0, x_amount)

                if evt is not None:
                    CGEventPost(kCGHIDEventTap, evt)
                    self._sleep_action_delay()
                    return
            except Exception:
                pass

        # Fallback using keyboard arrows
        key_map = {"up": 126, "down": 125, "left": 123, "right": 124}
        key_code = key_map.get(action.direction, 125)
        for _ in range(action.amount):
            self._send_key_combo(key_code=key_code, flags=0)
            time.sleep(0.02)
        self._sleep_action_delay()

    def _mouse_left_double_click(self, x: float, y: float) -> None:
        point = CGPointMake(x, y)
        try:
            from Quartz import CGEventSetIntegerValueField, kCGMouseEventClickState
        except ImportError:
            CGEventSetIntegerValueField = None
            kCGMouseEventClickState = None

        down1 = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, kCGMouseButtonLeft)
        up1 = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, kCGMouseButtonLeft)
        down2 = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, kCGMouseButtonLeft)
        up2 = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, kCGMouseButtonLeft)

        if CGEventSetIntegerValueField is not None and kCGMouseEventClickState is not None:
            try:
                CGEventSetIntegerValueField(down1, kCGMouseEventClickState, 1)
                CGEventSetIntegerValueField(up1, kCGMouseEventClickState, 1)
                CGEventSetIntegerValueField(down2, kCGMouseEventClickState, 2)
                CGEventSetIntegerValueField(up2, kCGMouseEventClickState, 2)
            except Exception:
                pass

        if down1 is None or up1 is None or down2 is None or up2 is None:
            raise ActionExecutionError("Failed to create double click mouse events.")

        CGEventPost(kCGHIDEventTap, down1)
        CGEventPost(kCGHIDEventTap, up1)
        time.sleep(0.05)
        CGEventPost(kCGHIDEventTap, down2)
        CGEventPost(kCGHIDEventTap, up2)

    def _mouse_right_click(self, x: float, y: float) -> None:
        point = CGPointMake(x, y)
        try:
            from Quartz import kCGEventRightMouseDown, kCGEventRightMouseUp, kCGMouseButtonRight
        except ImportError:
            kCGEventRightMouseDown = 3  # type: ignore[assignment]
            kCGEventRightMouseUp = 4  # type: ignore[assignment]
            kCGMouseButtonRight = 1  # type: ignore[assignment]

        down = CGEventCreateMouseEvent(None, kCGEventRightMouseDown, point, kCGMouseButtonRight)
        up = CGEventCreateMouseEvent(None, kCGEventRightMouseUp, point, kCGMouseButtonRight)

        if down is None or up is None:
            raise ActionExecutionError("Failed to create right click mouse events.")

        CGEventPost(kCGHIDEventTap, down)
        CGEventPost(kCGHIDEventTap, up)

    def _mouse_move(self, x: float, y: float) -> None:
        point = CGPointMake(x, y)
        move = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, kCGMouseButtonLeft)
        if move is None:
            raise ActionExecutionError("Failed to create mouse move events.")
        CGEventPost(kCGHIDEventTap, move)

    # -------------------------------------------------------------------------
    # Permissions / app resolution
    # -------------------------------------------------------------------------

    def ensure_accessibility_permissions(self, *, prompt: bool = True) -> None:
        options = {kAXTrustedCheckOptionPrompt: bool(prompt)}
        trusted = bool(AXIsProcessTrustedWithOptions(options))
        if not trusted:
            raise ActionExecutionError(
                "Accessibility permission not granted. "
                "Enable it in System Settings > Privacy & Security > Accessibility."
            )

    def _app_ref(self, bundle_id: str) -> Any:
        pid = self._pid_for_bundle_id(bundle_id)
        return AXUIElementCreateApplication(pid)

    def _pid_for_bundle_id(self, bundle_id: str) -> int:
        apps = NSRunningApplication.runningApplicationsWithBundleIdentifier_(bundle_id)
        if not apps:
            raise ActionExecutionError(f"No running app found for bundle_id={bundle_id!r}")

        # Prefer active/non-terminated instances if multiple exist.
        chosen = None
        for app in apps:
            if not bool(app.isTerminated()):
                chosen = app
                if bool(app.isActive()):
                    break

        if chosen is None:
            chosen = apps[0]

        pid = int(chosen.processIdentifier())
        if pid <= 0:
            raise ActionExecutionError(f"Resolved invalid PID for bundle_id={bundle_id!r}")
        return pid

    # -------------------------------------------------------------------------
    # Snapshot traversal
    # -------------------------------------------------------------------------

    def _best_root_element(self, app_ref: Any) -> Any:
        # Prefer focused window, then main window, then first windows entry, then app ref.
        for attr in (
            kAXFocusedWindowAttribute,
            kAXMainWindowAttribute,
            kAXWindowsAttribute,
        ):
            value = self._copy_attr(app_ref, attr)
            if value is None:
                continue

            if isinstance(value, (list, tuple)) and value:
                return value[0]
            return value

        return app_ref

    def _snapshot_element(
        self,
        *,
        element: Any,
        path: str,
        depth: int,
        bundle_id: str,
    ) -> AXNodeSnapshot:
        role = self._safe_str(self._copy_attr(element, kAXRoleAttribute)) or "AXUnknown"
        subrole = self._safe_str(self._copy_attr(element, kAXSubroleAttribute))
        title = self._safe_str(self._copy_attr(element, kAXTitleAttribute))
        description = self._safe_str(self._copy_attr(element, kAXDescriptionAttribute))
        value = self._safe_value(self._copy_attr(element, kAXValueAttribute))
        enabled = self._safe_bool(self._copy_attr(element, kAXEnabledAttribute), default=True)
        visible = self._safe_bool(self._copy_attr(element, kAXVisibleAttribute), default=True)
        focused = self._safe_bool(self._copy_attr(element, kAXFocusedAttribute), default=False)

        element_id = f"{bundle_id}:{path}"
        self._element_cache[element_id] = element

        children: list[AXNodeSnapshot] = []
        if depth < self.config.snapshot_max_depth:
            raw_children = self._copy_attr(element, kAXChildrenAttribute)
            if isinstance(raw_children, (list, tuple)):
                for idx, child in enumerate(raw_children[: self.config.snapshot_max_children]):
                    child_path = f"{path}/{idx}"
                    children.append(
                        self._snapshot_element(
                            element=child,
                            path=child_path,
                            depth=depth + 1,
                            bundle_id=bundle_id,
                        )
                    )
                    if self.config.traversal_delay_seconds > 0:
                        time.sleep(self.config.traversal_delay_seconds)

        return AXNodeSnapshot(
            element_id=element_id,
            role=role,
            subrole=subrole,
            title=title,
            description=description,
            value=value,
            enabled=enabled,
            visible=visible,
            focused=focused,
            children=children,
        )

    # -------------------------------------------------------------------------
    # AX actions / fallbacks
    # -------------------------------------------------------------------------

    def _try_ax_press(self, element: Any) -> bool:
        try:
            result = AXUIElementPerformAction(element, kAXPressAction)
            return self._is_ax_success(result)
        except Exception:
            return False

    def _element_center(self, element: Any) -> dict[str, float]:
        position = self._copy_attr(element, kAXPositionAttribute)
        size = self._copy_attr(element, kAXSizeAttribute)

        pos_x, pos_y = self._extract_point(position)
        width, height = self._extract_size(size)

        if pos_x is None or pos_y is None or width is None or height is None:
            raise ActionExecutionError(
                "Unable to resolve element screen coordinates for click fallback."
            )

        return {
            "x": pos_x + (width / 2.0),
            "y": pos_y + (height / 2.0),
        }

    def _mouse_left_click(self, x: float, y: float) -> None:
        point = CGPointMake(x, y)

        move_evt = CGEventCreateMouseEvent(None, kCGEventMouseMoved, point, kCGMouseButtonLeft)
        down_evt = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, kCGMouseButtonLeft)
        up_evt = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, kCGMouseButtonLeft)

        if move_evt is None or down_evt is None or up_evt is None:
            raise ActionExecutionError("Failed to create mouse click events.")

        CGEventPost(kCGHIDEventTap, move_evt)
        CGEventPost(kCGHIDEventTap, down_evt)
        CGEventPost(kCGHIDEventTap, up_evt)

    def _send_text(self, text: str) -> None:
        for ch in text:
            down = CGEventCreateKeyboardEvent(None, 0, True)
            up = CGEventCreateKeyboardEvent(None, 0, False)
            if down is None or up is None:
                raise ActionExecutionError("Failed to create unicode key events.")

            CGEventKeyboardSetUnicodeString(down, len(ch), ch)
            CGEventKeyboardSetUnicodeString(up, len(ch), ch)

            CGEventPost(kCGHIDEventTap, down)
            CGEventPost(kCGHIDEventTap, up)

    def _send_clear_shortcut(self) -> None:
        # Cmd+A then Delete (51)
        self._send_key_combo(key_code=0, flags=kCGEventFlagMaskCommand)  # A
        self._send_key_combo(key_code=51, flags=0)

    def _send_key_combo(self, *, key_code: int, flags: int) -> None:
        down = CGEventCreateKeyboardEvent(None, key_code, True)
        up = CGEventCreateKeyboardEvent(None, key_code, False)
        if down is None or up is None:
            raise ActionExecutionError("Failed to create key combo events.")

        try:
            down.setFlags_(flags)
            up.setFlags_(flags)
        except AttributeError:
            from Quartz import CGEventSetFlags  # type: ignore

            CGEventSetFlags(down, flags)
            CGEventSetFlags(up, flags)

        CGEventPost(kCGHIDEventTap, down)
        CGEventPost(kCGHIDEventTap, up)

    def _modifier_flags(self, modifiers: Iterable[Any]) -> int:
        flags = 0
        for modifier in modifiers:
            value = getattr(modifier, "value", modifier)
            if value == "command":
                flags |= int(kCGEventFlagMaskCommand)
            elif value == "shift":
                flags |= int(kCGEventFlagMaskShift)
            elif value == "option":
                flags |= int(kCGEventFlagMaskAlternate)
            elif value == "control":
                flags |= int(kCGEventFlagMaskControl)
        return flags

    # -------------------------------------------------------------------------
    # AX wrappers / bridge normalization
    # -------------------------------------------------------------------------

    def _copy_attr(self, element: Any, attribute: str) -> Any | None:
        try:
            raw = AXUIElementCopyAttributeValue(element, attribute, None)
        except TypeError:
            # Some bridge variants expose a 2-arg version returning (err, value)
            raw = AXUIElementCopyAttributeValue(element, attribute)
        except Exception:
            return None

        err, value = self._unwrap_ax_result(raw)
        if err != 0:
            return None
        return value

    def _set_attr(self, element: Any, attribute: str, value: Any) -> bool:
        try:
            raw = AXUIElementSetAttributeValue(element, attribute, value)
        except Exception:
            return False
        return self._is_ax_success(raw)

    def _unwrap_ax_result(self, raw: Any) -> tuple[int, Any | None]:
        # Common PyObjC patterns:
        # - (err, value)
        # - err
        # - value only
        if isinstance(raw, tuple):
            if len(raw) == 2 and isinstance(raw[0], int):
                return int(raw[0]), raw[1]
            if len(raw) == 1 and isinstance(raw[0], int):
                return int(raw[0]), None

        if isinstance(raw, int):
            return raw, None

        return 0, raw

    def _is_ax_success(self, raw: Any) -> bool:
        err, _ = self._unwrap_ax_result(raw)
        return err == 0

    def _resolve_cached_element(self, element_id: str) -> Any:
        try:
            return self._element_cache[element_id]
        except KeyError as exc:
            raise ActionExecutionError(
                f"Element {element_id!r} is not cached. Run snapshot() before action execution."
            ) from exc

    # -------------------------------------------------------------------------
    # Value coercion helpers
    # -------------------------------------------------------------------------

    def _safe_str(self, value: Any) -> str | None:
        if value is None:
            return None
        try:
            text = str(value).strip()
        except Exception:
            return None
        return text or None

    def _safe_bool(self, value: Any, *, default: bool) -> bool:
        if value is None:
            return default
        try:
            return bool(value)
        except Exception:
            return default

    def _safe_value(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        try:
            return str(value)
        except Exception:
            return None

    def _extract_point(self, value: Any) -> tuple[float | None, float | None]:
        # NSValue-backed CGPoint often stringifies like: "x, y" or "{{x, y}, ...}".
        # Try attribute access first, then string parsing fallback.
        for x_attr, y_attr in (("x", "y"), ("X", "Y")):
            x = getattr(value, x_attr, None)
            y = getattr(value, y_attr, None)
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                return float(x), float(y)

        try:
            text = str(value)
            nums = self._extract_numbers(text)
            if len(nums) >= 2:
                return nums[0], nums[1]
        except Exception:
            pass

        return None, None

    def _extract_size(self, value: Any) -> tuple[float | None, float | None]:
        for w_attr, h_attr in (("width", "height"), ("Width", "Height")):
            w = getattr(value, w_attr, None)
            h = getattr(value, h_attr, None)
            if isinstance(w, (int, float)) and isinstance(h, (int, float)):
                return float(w), float(h)

        try:
            text = str(value)
            nums = self._extract_numbers(text)
            if len(nums) >= 2:
                return nums[0], nums[1]
        except Exception:
            pass

        return None, None

    def _extract_numbers(self, text: str) -> list[float]:
        token = ""
        out: list[float] = []
        for ch in text:
            if ch.isdigit() or ch in ".-":
                token += ch
            else:
                if token and token not in {"-", ".", "-."}:
                    with contextlib.suppress(ValueError):
                        out.append(float(token))
                token = ""
        if token and token not in {"-", ".", "-."}:
            with contextlib.suppress(ValueError):
                out.append(float(token))
        return out

    def _sleep_action_delay(self) -> None:
        if self.config.action_delay_seconds > 0:
            time.sleep(self.config.action_delay_seconds)
