function set_visibility_name() {
    choice = document.getElementById("calc_type");
    field = document.getElementById("calc_name_field");
    if(!field) {
        console.log("Did not find an ensemble name (calc_name_field)")
        return;
    }
    if(ensemble == true) {
        if(choice.value == "Geometrical Optimisation" ||  choice.value == "Constrained Optimisation" || choice.value == "Conformational Search" ||  choice.value == "TS Optimisation" || choice.value == "Constrained Conformational Search" || choice.value == "Minimum Energy Path") {
            field.style.display = "block";
        }
        else {
            field.style.display = "none";
        }
    }
    else {
        field.style.display = "block";
    }
}
function calc_selection_changed() {
    {% if is_flowchart is None %}
        choice = document.getElementById("calc_type");
        if(choice.value == "Constrained Optimisation" || choice.value == "Constrained Conformational Search") {
            viewer.styles.atoms_displayLabels_3D = true;
        }
        else if(choice.value == "Minimum Energy Path") {
            viewer.styles.atoms_displayLabels_3D = false;
            refresh_aux_mol();
        }
        else {
            viewer.styles.atoms_displayLabels_3D = false;
        }

        if(choice.value == "Conformational Search" || choice.value == "Constrained Conformational Search") {
            // Hardcoded values for now...
            $("#cloud_num_cores").html({% if request.user.is_trial %}"4"{% else %}"8"{% endif %});
        }
        else {
            $("#cloud_num_cores").html("1 to 4");
        }

    {% endif %}
    set_visibility_name();
    refresh_availabilities();
}

