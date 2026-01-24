class BootstrapFormMixin:
    """
    Aplica automáticamente clases Bootstrap a los campos del formulario.
    Versión compacta: form-control-sm / form-select-sm.
    """

    size = "sm"  # "sm" | None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            widget = field.widget
            base_class = widget.attrs.get("class", "")

            is_select = widget.__class__.__name__ in ("Select", "SelectMultiple")

            if is_select:
                css_class = "form-select"
                if self.size == "sm":
                    css_class += " form-select-sm"
            else:
                css_class = "form-control"
                if self.size == "sm":
                    css_class += " form-control-sm"

            widget.attrs["class"] = (base_class + " " + css_class).strip()
