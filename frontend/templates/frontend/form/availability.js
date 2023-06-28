var master_list_params = ["software", "type", "solvent", "solvation_model", "solvation_radii", "theory_level", "driver", "resource"];
var master_options = {
    "software": {
        "Gaussian": {
            "type": ["NMR Prediction", "Geometrical Optimisation", "TS Optimisation", "Frequency Calculation", "Constrained Optimisation", "Single-Point Energy", "UV-Vis Calculation"],
            "solvation_model": ["PCM", "CPCM", "SMD"],
            "se_method": ["AM1", "PM3", "PM6", "PM7"],
            "solvation_radii": ["SMD18", "Default", "UFF", "UA0", "UAHF", "UAKS", "Pauling", "Bondi"],
            "theory_level": ["semiempirical", "hf", "dft"],
            "driver": ["Gaussian"]
        },
        "ORCA": {
            "type": ["NMR Prediction", "Geometrical Optimisation", "TS Optimisation", "Frequency Calculation", "Constrained Optimisation", "Single-Point Energy", "MO Calculation", "Minimum Energy Path"],
            "solvation_model": ["CPCM", "SMD"],
            "se_method": ["AM1", "PM3"],
            "solvation_radii": ["SMD18", "Default"],
            "theory_level": ["semiempirical", "hf", "dft", "mp2"],
            "driver": ["ORCA", "Pysisyphus"]
        },
        "xtb": {
            "type": ["Geometrical Optimisation", "TS Optimisation", "Frequency Calculation", "Constrained Optimisation", "Single-Point Energy", "UV-Vis Calculation", "Conformational Search", "Constrained Conformational Search", "Minimum Energy Path"],
            "solvation_model": ["ALPB", "GBSA"],
            "solvation_radii": ["Default"],
            "theory_level": ["xtb"],
            "driver": ["xtb", "Pysisyphus", "ORCA"]
        },
        "NWChem": {
            "type": ["Single-Point Energy", "MO Calculation", "ESP Calculation", "Geometrical Optimisation", "Frequency Calculation"],
            "theory_level": ["hf", "dft"],
            "driver": ["NWChem"],
            "solvation_model": [],
        },
    },
    "solvation_model": {
        "SMD": {
            "solvation_radii": ["Default", "SMD18"],
        },
        "PCM": {
            "solvation_radii": ["Default", "UFF", "UA0", "UAHF", "UAKS", "Pauling", "Bondi"],
        },
        "CPCM": {
            "solvation_radii": ["Default", "UFF", "UA0", "UAHF", "UAKS", "Pauling", "Bondi"],
        },
        "GBSA": {
            "solvation_radii": ["Default"],
        },
        "ALPB": {
            "solvation_radii": ["Default"],
        }
    },
    "type": {
        "Minimum Energy Path": {
            "driver": ["ORCA", "Pysisyphus"]
        },
        "NMR Prediction": {
            "driver": ["ORCA", "Gaussian", "NWChem"]
        }, 
        "Geometrical Optimisation": {
            "driver": ["xtb", "Gaussian", "ORCA", "NWChem"]
        }, 
        "TS Optimisation": {
            "driver": ["Pysisyphus", "Gaussian", "ORCA", "NWChem"]
        }, 
        "Frequency Calculation": {
            "driver": ["xtb", "Gaussian", "ORCA", "NWChem"]
        }, 
        "Constrained Optimisation": {
            "driver": ["xtb", "Gaussian", "ORCA", "NWChem"]
        }, 
        "Single-Point Energy": {
            "driver": ["xtb", "Gaussian", "ORCA", "NWChem"]
        }, 
        "MO Calculation": {
            "driver": ["ORCA", "NWChem"]
        }, 
        "UV-Vis Calculation": {
            "driver": ["ORCA", "Gaussian", "xtb"]
        }, 
        "Conformational Search": {
            "driver": ["xtb"]
        }, 
        "Constrained Conformational Search": {
            "driver": ["xtb"]
        }
    },
    "resource": {
        "Local": {
            "driver": [{% if "Gaussian" in packages %}"Gaussian", {% endif %}{% if "ORCA" in packages %}"ORCA", {% endif %}"Pysisyphus", "xtb", "NWChem"],
            "software": [{% if "Gaussian" in packages %}"Gaussian", {% endif %}{% if "ORCA" in packages %}"ORCA", {% endif %} "xtb", "NWChem"]
        }
    }
}
var list_available_elements = ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "xtb_method", "basis_set_field", "custom_bs", "aux_file_structure", "aux_structure", "solvation_model", "solvation_radii", "constraints"];
var master_available = {
    "software": {
        "Gaussian": ["df", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "constraints"],
        "ORCA": ["hf3c", "pbeh3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "constraints", "aux_file_structure", "aux_structure"],
        "xtb": ["aux_file_structure", "aux_structure", "solvation_model", "solvation_radii", "constraints", "xtb_method"],
        "NWChem": ["functional_field", "basis_set_field"],
    },
    "theory_level": {
        "xtb": ["aux_file_structure", "aux_structure", "solvation_model", "solvation_radii", "constraints", "xtb_method"],
        "semiempirical": ["aux_file_structure", "aux_structure", "se_method", "solvation_model", "solvation_radii", "constraints"],
        "hf": ["aux_file_structure", "aux_structure", "hf3c", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "constraints"],
        "dft": ["aux_file_structure", "aux_structure", "df", "pbeh3c", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "constraints"],
        "mp2": ["aux_file_structure", "aux_structure", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "constraints"]
    },
    "type": {
        "Minimum Energy Path": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "aux_file_structure", "aux_structure", "solvation_model", "solvation_radii", "xtb_method"],
        "NMR Prediction": ["df", "pbeh3c", "hf3c", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii"],
        "Geometrical Optimisation": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "xtb_method"],
        "TS Optimisation": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "xtb_method"],
        "Frequency Calculation": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "xtb_method"],
        "Constrained Optimisation": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "constraints", "xtb_method"],
        "Single-Point Energy": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "xtb_method"],
        "MO Calculation": ["df", "pbeh3c", "hf3c", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii"],
        "UV-Vis Calculation": ["df", "pbeh3c", "hf3c", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "xtb_method"],
        "Conformational Search": ["solvation_model", "solvation_radii", "xtb_method"],
        "Constrained Conformational Search": ["solvation_model", "solvation_radii", "constraints", "xtb_method"]
    },
    "solvent": {
        "": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "aux_file_structure", "aux_structure", "constraints", "xtb_method"]
    }
}

function refresh_availabilities() {
    // Since some parameters that will change can influence which parameters should be visible, we have to execute the function twice
    _refresh_availabilities();
    _refresh_availabilities();
}

function _refresh_availabilities() {
    full_options = document.querySelectorAll(".unavailable");
    full_options.forEach(element => {
        element.classList.remove("unavailable");
        element.style.display = 'block';
    });

    master_list_params.forEach(p => {
        el = document.getElementsByName("calc_"+p)[0];
        // Some elements can be omitted when generating the page depending on the parameters 
        // (e.g., launching from ensemble)
        if(el != undefined) {
            choice = el.value;
            if (p in master_options && choice in master_options[p]) {
                for (const key2 in master_options[p][choice]) {
                    el2 = document.getElementsByName("calc_"+key2)[0];
                    allowed = master_options[p][choice][key2];
                    for (let opt of el2.options) {
                        if(!allowed.includes(opt.value)) {
                            opt.style.display = "none";
                            opt.classList.add("unavailable");
                        }
                    }
                }
            }
            if (p in master_available && choice in master_available[p]) {
                for (const ind in list_available_elements) {
                    key = list_available_elements[ind];
                    el2 = document.getElementById("calc_"+key);
                    if(el2 != undefined) {
                        if(!master_available[p][choice].includes(key)) {
                            el2.style.display = "none";
                            el2.classList.add("unavailable");
                        }
                    }
                }
            }
        }
    });

    try {
        software = document.getElementById("calc_software").value;
        if(software == "Gaussian") {
            document.querySelectorAll(".scan_from").forEach(element => {
                if(!element.classList.contains("unavailable")) {
                    element.style.display = "none";
                    element.classList.add("unavailable");
                }
            });
        }
    }
    catch (excp) {
        console.log("No software element found.")
    }
    set_availables();

    /* hide columns with hidden content */
    columns = document.querySelectorAll(".column.optional-column");
    columns.forEach(element => {
        element.style.display = "none";
        $(element).children("div:not(unavailable)").each((ind, subel) => {
            if(subel.style.display != "none")
            {
                $(element).show();
            }
        });
    });
}

function set_availables() {
    [].forEach.call(document.getElementById("parameters_div").querySelectorAll('select'), function(sel) {
        ind = sel.selectedIndex;
        if(ind != -1) {
            opt = sel.options[ind];
            if(opt.style.display != "none" && !opt.disabled) {
                return;
            }
        }

        // If there is a preferred option set (by being tagged "selected"), pick that one
        // Otherwise, pick any valid option
        for(i=0; i < sel.options.length; i++) {
            opt = sel.options[i];
            if(opt.getAttribute("selected") != undefined && opt.style.display != "none"  && !opt.disabled) {
                sel.selectedIndex = i;
                return
            }
        }
        for(i=0; i < sel.options.length; i++) {
            opt = sel.options[i];
            if(opt.style.display != "none"  && !opt.disabled) {
                sel.selectedIndex = i;
                return
            }
        }

    });
}

