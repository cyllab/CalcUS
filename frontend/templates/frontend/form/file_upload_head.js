function set_time_estimation_unavailable() {
    let estimation = document.getElementById("calc_time_estimation");
    let advice = document.getElementById("calc_time_advice");
    $(estimation).html("");
    $(advice).html("");
    if(estimation.classList.contains("red"))
        estimation.classList.remove("red");
}
function update_time_estimation() {
    let choice = document.getElementById("calc_type");
    
    if(!(choice.value == "Conformational Search" ||choice.value == "Constrained Conformational Search")) {
        set_time_estimation_unavailable();
        return;
    }

    let natoms = 0;
    for(i=0; i<viewer.molecules.length; i++) {
        natoms += viewer.molecules[i].atoms.length;
    }

    if(natoms == 0) {
        set_time_estimation_unavailable();
        return;
    }
    let method = document.getElementsByName("calc_xtb_method")[0].value;

    let estim_low;
    let estim_high;
    if(method == "gfn2-xtb") {
        estim_low = 295.221*Math.exp(0.063*natoms);
        estim_high = 54.435*Math.exp(0.152*natoms);
    }
    else if(method == "gfn-ff") {
        estim_low = 41.352*Math.exp(0.041*natoms);
        estim_high = 7.353*Math.exp(0.146*natoms);
    }
    else {
        set_time_estimation_unavailable();
        return;
    }
    
    let estimation = document.getElementById("calc_time_estimation");
    $(estimation).html("Estimated runtime: between " + estim_low.toPrecision(3) + " and " + estim_high.toPrecision(3) + " CPU seconds");

    {% if IS_CLOUD %}
    let advice = document.getElementById("calc_time_advice");

    if(estim_low*2 > {{ request.user.remaining_time }}) {
        estimation.classList.add("red");
        if (method == "gfn2-xtb") {
            $(advice).html("You will likely run out of computing time with this conformational search, consider getting more computing time or using GFN-FF.");
        }
        else {
            $(advice).html("You will likely run out of computing time with this conformational search, consider getting more computing time.");
        }
    }
    {% endif %}

}
function file_upload_changed() {
    file_list = this.files;
    add_file_name();	
    preview_upload(file_list);

    ff = file_list[0].name;
    fname = ff.replace('C:\\fakepath\\', '');
    if(file_list.length > 1) {
        fname += ', ...';
    }

    $("#file_upload_name").html(fname);

    combine = document.getElementById("calc_combine_files_column");
    parse  = document.getElementById("calc_parse_filenames_column");
    if (file_list.length > 1) {
        combine.style.display = "block";	
        parse.style.display = "block";	
    }
    else {
        combine.style.display = "none";	
        parse.style.display = "none";	
    }
    setTimeout(function() {
        update_time_estimation();
    }, 500);
}
function aux_file_upload_changed() {
    file_list = this.files;
    ff = file_list[0].name;
    fname = ff.replace('C:\\fakepath\\', '');
    if(file_list.length > 1) {
        fname += ', ...';
    }

    $("#aux_file_upload_name").html(fname);
    if(fname.length > 1)
        $("#calc_aux_structure").hide()
    else
        $("#calc_aux_structure").show()
}
function toggle_visibility_molname(check) {
    if(check.checked) {
        $("#calc_mol_name_field").hide();
    }
    else{
        $("#calc_mol_name_field").show();
    }
}
function add_file_name() {
    path = $("#file_structure").val();
    file_name = path.replace('C:\\fakepath\\', '').split('.')[0];
    curr_name = document.getElementById("calc_mol_name").value;
    if(curr_name == "") {
        $("#calc_mol_name").val(file_name);
    }
}
