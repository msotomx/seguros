def user_role_context(request):
    user = request.user

    if not user.is_authenticated:
        return {
            "current_role": "",
            "current_role_label": "",
        }

    if (user.is_superuser):
        role = "SUPERADMIN"
        label = "Super Administrador"
    else:
        groups = list(user.groups.values_list("name", flat=True))

        if "Admin" in groups:
            role = "SUPERADMIN"
            label = "Super Administrador"
        elif "Supervisor" in groups:
            role = "SUPERVISOR"
            label = "Supervisor"
        elif "Agente" in groups:
            role = "AGENTE"
            label = "Agente"
        elif "Operador" in groups:
            role = "OPERADOR"
            label = "Operador"
        elif "Lectura" in groups:
            role = "LECTURA"
            label = "Lectura"
        else:
            role = "USUARIO"
            label = "Usuario"

    return {
        "current_role": role,
        "current_role_label": label,
    }
