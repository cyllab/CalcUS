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
