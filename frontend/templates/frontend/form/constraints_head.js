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

function add_constraint(first) {
    constraint_num += 1;

    _line = `
    <div class="control" id="constraint_{}"> \
        <div class="columns"> \
            <div class="column"> \
                <div class="select"> \
                    <select name="constraint_mode_{}" id="constraint_mode_{}" onchange="constraint_mode_changed({})"> \
                    <option>Freeze</option> \
                    <option>Scan</option> \
                    </select> \
                </div> \
            </div> \
            <div class="column"> \
                <div class="select"> \
        <select name="constraint_type_{}" id="constraint_type_{}" onchange="constraint_type_selection_changed({});"> \
                    <option>Distance</option> \
                    <option>Angle</option> \
                    <option>Dihedral</option> \
                    </select> \
                </div> \
            </div> \
            <div class="column"> \
                <input class="input" type="text" width="5" name="calc_constraint_{}_1" id="calc_constraint_{}_1"> \
            </div> \
            <div class="column"> \
                <input class="input" type="text" width="5" name="calc_constraint_{}_2" id="calc_constraint_{}_2"> \
            </div> \
            <div class="column"> \
                <input class="input" type="text" width="5" name="calc_constraint_{}_3" id="calc_constraint_{}_3" style="display: none;"> \
            </div> \
            <div class="column"> \
                <input class="input" type="text" width="5" name="calc_constraint_{}_4" id="calc_constraint_{}_4" style="display: none;"> \
            </div> \
            <div class="column"> \
        <button type="button" class="button is-danger constraint_btn" onclick="$('#calc_scan_div_{}').remove(); $(this).parent().parent().parent().remove();">-</button> \
            </div> \
        </div> \
    </div> \
        <div style="display: none;" id="calc_scan_div_{}"> \
        <div class="columns"> \
        <div class="column"> \
            <p id="calc_label_from_{}"> From (Å)</p> \
        <input class="input scan_from" type="text" width="5" name="calc_scan_{}_1" id="calc_scan_{}_1"> \
        </div> \
        <div class="column"> \
            <p id="calc_label_to_{}"> To (Å)</p> \
        <input class="input" type="text" width="5" name="calc_scan_{}_2" id="calc_scan_{}_2"> \
        </div> \
        <div class="column"> \
            # Steps \
        <input class="input" type="text" width="5" name="calc_scan_{}_3" id="calc_scan_{}_3"> \
        </div> \
    </div> \
    </div>`.format(constraint_num);
    if(first) {
        _line = _line.replace(`<button type="button" class="button is-danger constraint_btn" onclick="$('#calc_scan_div_{}').remove(); $(this).parent().parent().parent().remove();">-</button>`.format(constraint_num), `<button type="button" class="button is-primary constraint_btn" id="add_constraint_btn" onclick="add_constraint();">+</button>`);
    }

    $("#constraint_list").append(_line);
}

