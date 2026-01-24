class BootstrapFormMixin:
    """
    Aplica automáticamente estilos Bootstrap a los formularios.
    Usa versión compacta (sm) para inputs y selects.
    """

    size = "sm"  # "sm" | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            widget = field.widget
            base_class = widget.attrs.get("class", "")

            is_select = widget.__class__.__name__ in (
                "Select",
                "SelectMultiple",
            )

            if is_select:
                css_class = "form-select"
                if self.size == "sm":
                    css_class += " form-select-sm"
            else:
                css_class = "form-control"
                if self.size == "sm":
                    css_class += " form-control-sm"

            widget.attrs["class"] = (base_class + " " + css_class).strip()


class BootstrapFormMixin2:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if field.widget.__class__.__name__ == "Select":
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")
