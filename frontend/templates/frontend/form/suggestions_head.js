function select_gfn2() {
    software = document.getElementsByName("calc_software")[0];
    if(software)
	    software.value = "xtb";

    theory_level = document.getElementsByName("calc_theory_level")[0];
    if(theory_level)
	    theory_level.value = "xtb";

    refresh_availabilities();

    method = document.getElementsByName("calc_xtb_method")[0];
    if(method)
	    method.value = "gfn2-xtb";
}

function select_gfnff() {
    software = document.getElementsByName("calc_software")[0];
    if(software)
	    software.value = "xtb";

    theory_level = document.getElementsByName("calc_theory_level")[0];
    if(theory_level)
	    theory_level.value = "xtb";

    refresh_availabilities();

    method = document.getElementsByName("calc_xtb_method")[0];
    if(method)
	    method.value = "gfn-ff";
}

function select_m062x_svp() {
    software = document.getElementsByName("calc_software")[0];
    if(software)
	    software.value = "NWChem";

    theory_level = document.getElementsByName("calc_theory_level")[0];
    if(theory_level)
	    theory_level.value = "dft";

    refresh_availabilities();

    method = document.getElementsByName("calc_functional")[0];
    if(method)
	    method.value = "M062X";

    bs = document.getElementsByName("calc_basis_set")[0];
    if(bs)
	    bs.value = "Def2-SVP";
}

function select_m062x_tzvp() {
    software = document.getElementsByName("calc_software")[0];
    if(software)
	    software.value = "NWChem";

    theory_level = document.getElementsByName("calc_theory_level")[0];
    if(theory_level)
	    theory_level.value = "dft";

    refresh_availabilities();

    method = document.getElementsByName("calc_functional")[0];
    if(method)
	    method.value = "M062X";

    bs = document.getElementsByName("calc_basis_set")[0];
    if(bs)
	    bs.value = "Def2-TZVP";
}
