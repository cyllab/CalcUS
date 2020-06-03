solvent = document.getElementById("calc_solvent");
solvent.value = "{{ params.solvent }}";

charge = document.getElementById("calc_charge");
charge.value = "{{ params.charge }}";

software = document.getElementById("calc_software");
software.value = "{{ params.software }}";

theory_level = document.getElementById("calc_theory_level");
theory_level.value = "{{ params.theory_level }}";

basis_set = document.getElementById("calc_basis_set");
basis_set.value = "{{ params.basis_set }}";

{% if params.method == "PBEh-3c" %}
	pbeh3c = document.getElementById("pbeh3c");
	pbeh3c.checked = true;
{% endif %}

{% if params.method == "HF-3c" %}
	hf3c = document.getElementById("hf3c");
	hf3c.checked = true;
{% endif %}

misc = document.getElementById("calc_misc");
misc.value = "{{ params.misc }}";

