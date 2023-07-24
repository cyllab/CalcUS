if ("{{ params.software }}" != "Unknown" && "{{ params.software }}" != "Open Babel") {
	solvent = document.getElementsByName("calc_solvent")[0];
    if(solvent)
	    solvent.value = "{{ params.solvent }}";

	solvation_model = document.getElementsByName("calc_solvation_model")[0];
    if(solvation_model)
	    solvation_model.value = "{{ params.solvation_model }}";

	solvation_radii = document.getElementsByName("calc_solvation_radii")[0];
    if(solvation_radii)
	    solvation_radii.value = "{{ params.solvation_radii }}";

	software = document.getElementsByName("calc_software")[0];
    if(software)
	    software.value = "{{ params.software }}";

	theory_level = document.getElementsByName("calc_theory_level")[0];
    if(theory_level)
	    theory_level.value = "{{ params.theory_level }}";


	basis_set = document.getElementsByName("calc_basis_set")[0];
    if(basis_set)
	    basis_set.value = "{{ params.basis_set }}";

	{% if params.method == "PBEh-3c" %}
		pbeh3c = document.getElementsByName("pbeh3c")[0];
        if(pbeh3c)
		    pbeh3c.checked = true;
	{% elif params.method == "HF-3c" %}
		hf3c = document.getElementsByName("hf3c")[0];
        if(hf3c)
		    hf3c.checked = true;
	{% elif params.software == "xtb" %}
        xtb_level = document.getElementsByName("calc_xtb_method")[0];
        if(xtb_level)
            xtb_level.value = "{{ params.method }}";
	{% else %}
		func = document.getElementsByName("calc_functional")[0];
        if(func)
		    func.value = "{{ params.method }}";
	{% endif %}
	
	{% if load_charge %}
		charge = document.getElementsByName("calc_charge")[0];
        if(charge)
		    charge.value = "{{ params.charge }}";
		mult = document.getElementsByName("calc_multiplicity")[0];
        if(mult)
		    mult.value = "{{ params.multiplicity }}";
	{% endif %}

	df = document.getElementsByName("calc_df")[0];
    if(df)
	    df.value = "{{ params.density_fitting }}";

	bs = document.getElementsByName("calc_custom_bs")[0];
    if(bs)
	    bs.value = "{{ params.custom_basis_sets }}";

    if("{{ params.software }}" != "xtb") {
        specifications = document.getElementsByName("calc_specifications")[0];
        if(specifications)
            specifications.value = "{{ params.specifications }}";
    }
}
