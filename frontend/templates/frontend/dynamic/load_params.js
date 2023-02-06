if ("{{ params.software }}" != "Unknown" && "{{ params.software }}" != "Open Babel") {
	solvent = document.getElementsByName("calc_solvent")[0];
	solvent.value = "{{ params.solvent }}";

	solvation_model = document.getElementsByName("calc_solvation_model")[0];
	solvation_model.value = "{{ params.solvation_model }}";

	solvation_radii = document.getElementsByName("calc_solvation_radii")[0];
	solvation_radii.value = "{{ params.solvation_radii }}";

	software = document.getElementsByName("calc_software")[0];
	software.value = "{{ params.software }}";

	theory_level = document.getElementsByName("calc_theory_level")[0];
	theory_level.value = "{{ params.theory_level }}";

	basis_set = document.getElementsByName("calc_basis_set")[0];
	basis_set.value = "{{ params.basis_set }}";

	{% if params.method == "PBEh-3c" %}
		pbeh3c = document.getElementsByName("pbeh3c")[0];
		pbeh3c.checked = true;
	{% elif params.method == "HF-3c" %}
		hf3c = document.getElementsByName("hf3c")[0];
		hf3c.checked = true;
	{% else %}
		func = document.getElementsByName("calc_functional")[0];
		func.value = "{{ params.method }}";
	{% endif %}
	
	{% if load_charge %}
		charge = document.getElementsByName("calc_charge")[0];
		charge.value = "{{ params.charge }}";
		mult = document.getElementsByName("calc_multiplicity")[0];
		mult.value = "{{ params.multiplicity }}";
	{% endif %}

	df = document.getElementsByName("calc_df")[0];
	df.value = "{{ params.density_fitting }}";

	bs = document.getElementsByName("calc_custom_bs")[0];
	bs.value = "{{ params.custom_basis_sets }}";

    if("{{ params.software }}" != "xtb") {
        specifications = document.getElementsByName("calc_specifications")[0];
        specifications.value = "{{ params.specifications }}";
    }
}
