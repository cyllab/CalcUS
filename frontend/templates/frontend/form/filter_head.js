function filter_changed() {
    choice = document.getElementById("calc_filter");
    value_input = document.getElementById("calc_filter_value");
    param_input = document.getElementById("calc_filter_params");
    label = document.getElementById("filter_label");
    if(choice.value == "None") {
        value_input.style.display = "none";
        param_input.style.display = "none";
    }
    else if(choice.value == "By Boltzmann Weight") {
        value_input.style.display = "block";
        param_input.style.display = "block";
        label.innerHTML = "Higher than";
    }
    else if(choice.value == "By Relative Energy") {
        value_input.style.display = "block";
        param_input.style.display = "block";
        label.innerHTML = "Lower than (" + "{{ profile.pref_units_name }}" + ")";
    }
}

