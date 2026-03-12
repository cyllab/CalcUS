if ("{{ params.software }}" != "Unknown" && "{{ params.software }}" != "Open Babel") {
    function setFieldValue(name, value) {
        field = document.getElementsByName(name)[0];
        if(field)
            field.value = value;
        return field;
    }

    function applySolvationFields() {
        solvent = setFieldValue("calc_solvent", "{{ params.solvent }}");
        if(solvent) {
            solvent.dispatchEvent(new Event("input", {bubbles: true}));
            solvent.dispatchEvent(new Event("change", {bubbles: true}));
        }

        setFieldValue("calc_solvation_model", "{{ params.solvation_model }}");
        setFieldValue("calc_solvation_radii", "{{ params.solvation_radii }}");
    }

	software = document.getElementsByName("calc_software")[0];
    if(software)
	    software.value = "{{ params.software }}";

	theory_level = document.getElementsByName("calc_theory_level")[0];
    if(theory_level)
	    theory_level.value = "{{ params.theory_level }}";

    function stabilizeSolvationFields(attempt) {
        applySolvationFields();
        if(attempt < 4)
            setTimeout(function() { stabilizeSolvationFields(attempt + 1); }, 100);
    }

    stabilizeSolvationFields(0);
    refresh_availabilities();
    stabilizeSolvationFields(0);

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
