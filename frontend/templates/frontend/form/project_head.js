function project_selection_changed(choice) {
    field = document.getElementById("new_project_name_field");
    if(choice.value == "New Project") {
        field.style.display = "block";
    }
    else {
        field.style.display = "none";	
        if(project_presets[choice.value] != -1) {
            load_preset(project_presets[choice.value]);
        }
        type = document.getElementById("calc_type");
        if(type.value == "Minimum Energy Path") {
            refresh_aux_mol();
        }

    }
}

function preselect_last_project() {
    $("#calc_project").val(localStorage.getItem("lastSelectedProject"));
}

function set_project_default() {
    $.ajax({
        data: $("#calcform").serialize(),
        headers: {
            "X-CSRFToken": '{{ csrf_token }}',
        },

        type: "POST",
        url: "/set_project_default/",
        success: function (response) {
            $("#preset_msg").html(response);
            refresh_presets();
        }
    });
}
var project_presets = {
    {% for proj in profile.project_set.all %}
    '{{ proj.name }}': {% if proj.preset %}"{{ proj.preset.id }}"{% else %} -1 {% endif %},
    {% endfor %}
}
