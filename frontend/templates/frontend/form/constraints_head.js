function constraint_type_selection_changed(id) {
    choice = document.getElementById("constraint_type_{}".format(id));
    inp2 = document.getElementById("calc_constraint_{}_2".format(id));
    inp3 = document.getElementById("calc_constraint_{}_3".format(id));
    inp4 = document.getElementById("calc_constraint_{}_4".format(id));
    from = document.getElementById("calc_label_from_{}".format(id));
    to = document.getElementById("calc_label_to_{}".format(id));

    if (choice.value == "Distance") {
        inp2.style.display = "block";
        inp3.style.display = "none";
        inp4.style.display = "none";
        from.innerHTML = "From (Å)";
        to.innerHTML = "To (Å)";
    }
    else if (choice.value == "Angle") {
        inp2.style.display = "block";
        inp3.style.display = "block";
        inp4.style.display = "none";
        from.innerHTML = "From (°)";
        to.innerHTML = "To (°)";
    }
    else {
        inp2.style.display = "block";
        inp3.style.display = "block";
        inp4.style.display = "block";
        from.innerHTML = "From (°)";
        to.innerHTML = "To (°)";
    }
}

function constraint_mode_changed(id) {
    choice = document.getElementById("constraint_mode_{}".format(id));
    div = document.getElementById("calc_scan_div_{}".format(id));
    if (choice.value == "Freeze") {
        div.style.display = "none";
    }
    else if (choice.value == "Scan") {
        div.style.display = "block";
    }
    refresh_availabilities();
}

