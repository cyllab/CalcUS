var master_list_params = ["software", "type", "solvent", "solvation_model", "solvation_radii", "theory_level", "driver", "resource"];
var master_options = {
    "type": {
        "Minimum Energy Path": {
            "software": ["xtb", "ORCA"],
            "driver": ["ORCA", "Pysisyphus"]
        },
        "NMR Prediction": {
            "software": ["ORCA", "Gaussian", "NWChem"],
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
            "software": ["ORCA", "NWChem", "xtb"],
            "driver": ["ORCA", "NWChem", "xtb"],
            "theory_level": ["hf", "dft", "mp2", "xtb"]
        }, 
        "UV-Vis Calculation": {
            "software": ["ORCA", "Gaussian", "xtb"],
            "driver": ["ORCA", "Gaussian", "xtb"]
            {% if interface == "simple" and IS_CLOUD %}
            , "theory_level": ["xtb"]
            {% endif %}
        }, 
        "ESP Calculation": {
            "software": ["NWChem"],
            "driver": ["NWChem"],
            "theory_level": ["hf", "dft"]
        },
        "Conformational Search": {
            "software": ["xtb"],
            "driver": ["xtb"],
            "theory_level": ["xtb"]
        }, 
        "Fast Conformational Search": {
            "software": ["xtb"],
            "driver": ["xtb"], // Not quite true, but good enough for now
            "theory_level": ["xtb"]
        }, 
        "Constrained Conformational Search": {
            "software": ["xtb"],
            "driver": ["xtb"],
            "theory_level": ["xtb"]
        }
    },
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
            "type": ["Geometrical Optimisation", "TS Optimisation", "Frequency Calculation", "Constrained Optimisation", "Single-Point Energy", "UV-Vis Calculation", "Conformational Search", "Constrained Conformational Search", "Minimum Energy Path", "Fast Conformational Search", "MO Calculation"],
            "solvation_model": ["ALPB", "GBSA"],
            "solvation_radii": ["Default"],
            "theory_level": ["xtb"],
            "driver": ["xtb", "Pysisyphus", "ORCA"]
        },
        "NWChem": {
            "type": ["Single-Point Energy", "MO Calculation", "ESP Calculation", "Geometrical Optimisation", "Frequency Calculation"],
            "theory_level": ["hf", "dft"],
            "driver": ["NWChem"],
            "solvation_model": ["COSMO", "SMD"],
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
        },
        "COSMO": {
            "solvation_radii": ["Default"],
        }
    },
    "resource": {
        "Local": {
            "driver": [{% if "Gaussian" in packages %}"Gaussian", {% endif %}{% if "ORCA" in packages %}"ORCA", {% endif %}"Pysisyphus", "xtb", "NWChem"],
            "software": [{% if "Gaussian" in packages %}"Gaussian", {% endif %}{% if "ORCA" in packages %}"ORCA", {% endif %} "xtb", "NWChem"]
        }
    }
    {% if is_batch %},
    /*
     * Inverse restrictions (children restricting parents)
     * Should only be used when the children can be toggled "on" or "off", 
     * so that the options aren't deadlocked (children preventing the parents from changing, 
     * while the parents prevent the children from changing).
     * */
    "theory_level": {
        "xtb": {
            "software": ["xtb"]
        },
        "semiempirical": {
            "software": ["Gaussian", "ORCA"]
        },
        "hf": {
            "software": ["Gaussian", "ORCA", "NWChem"]
        },
        "dft": {
            "software": ["Gaussian", "ORCA", "NWChem"]
        },
        "mp2": {
            "software": ["ORCA"]
        }

    }
    {% endif %}
}
var list_available_elements = ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "xtb_method", "basis_set_field", "custom_bs", "aux_file_structure", "aux_structure", "solvation_model", "solvation_radii", "constraints", "new_type_badge"];
var master_available = {
    "software": {
        "Gaussian": ["df", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "constraints"],
        "ORCA": ["hf3c", "pbeh3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "constraints", "aux_file_structure", "aux_structure"],
        "xtb": ["aux_file_structure", "aux_structure", "solvation_model", "solvation_radii", "constraints", "xtb_method", "new_type_badge"],
        "NWChem": ["functional_field", "basis_set_field", "solvation_model", "solvation_radii"],
    },

    "theory_level": {
        "xtb": ["aux_file_structure", "aux_structure", "solvation_model", "solvation_radii", "constraints", "xtb_method", "new_type_badge"],
        "semiempirical": ["aux_file_structure", "aux_structure", "se_method", "solvation_model", "solvation_radii", "constraints"],
        "hf": ["aux_file_structure", "aux_structure", "hf3c", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "constraints"],
        "dft": ["aux_file_structure", "aux_structure", "df", "pbeh3c", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "constraints"]
        , "mp2": ["aux_file_structure", "aux_structure", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "constraints"]
    },
    "type": {
        "Minimum Energy Path": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "aux_file_structure", "aux_structure", "solvation_model", "solvation_radii", "xtb_method"],
        "NMR Prediction": ["df", "pbeh3c", "hf3c", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii"],
        "Geometrical Optimisation": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "xtb_method"],
        "TS Optimisation": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "xtb_method"],
        "Frequency Calculation": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "xtb_method"],
        "Constrained Optimisation": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "constraints", "xtb_method"],
        "Single-Point Energy": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "xtb_method"],
        "ESP Calculation": ["functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii"],
        "MO Calculation": ["df", "pbeh3c", "hf3c", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii"],
        "UV-Vis Calculation": ["df", "pbeh3c", "hf3c", "functional_field", "basis_set_field", "custom_bs", "solvation_model", "solvation_radii", "xtb_method"],
        "Conformational Search": ["solvation_model", "solvation_radii", "xtb_method"],
        "Fast Conformational Search": ["solvation_model", "solvation_radii", "xtb_method", "new_type_badge"],
        "Constrained Conformational Search": ["solvation_model", "solvation_radii", "constraints", "xtb_method"]
    },
    "solvent": {
        "": ["df", "pbeh3c", "hf3c", "se_method", "functional_field", "basis_set_field", "custom_bs", "aux_file_structure", "aux_structure", "constraints", "xtb_method", "new_type_badge"]
    }
}

var parameters_dependencies = {
    "method": ["theory_level"],
    "basis_set": ["theory_level"],
    "driver": ["software"],
    "solvation_radii": ["solvent"],
    "solvation_model": ["solvent"],
}

function refresh_availabilities(context, target, additive) {
    // Since some parameters that will change can influence which parameters should be visible, we have to execute the function twice
    _refresh_availabilities(context, target, additive);
    _refresh_availabilities(context, target, additive);
}

function _refresh_availabilities(context, target, additive) {
    if(context == undefined)
        context = $("#parameters_div")

    if(target == undefined)
        target = context;

    if(!additive) {
        full_options = $(target).find(".unavailable").each(function() {
            $(this).removeClass("unavailable");
        });
    }

    master_list_params.forEach(p => {
        el = $(context).find("[name='calc_"+p+"']")[0];
        
        // Some elements can be omitted when generating the page depending on the parameters 
        // (e.g., launching from ensemble)
        if(el != undefined) {
            {% if is_batch %}
            // We only want to hide options if the parameter is chosen as fixed.
            // Ignore the cases where the structure is different (outside the fixed parameters section)
            try {
                let parent_row = el.closest(".columns");
                checkbox = $(parent_row).find(".column.is-1 > input");
                if(checkbox.length > 0 && (!checkbox.prop('checked') || checkbox.prop('disabled')))
                    return
            }
            catch(TypeError) {}
            {% endif %}

            let choice = el.value;

            if (p in master_options && choice in master_options[p]) {
                for (const key2 in master_options[p][choice]) {
                    try {
                        let el2 = $(target).find("[name='calc_" + key2 + "']")[0];
                        allowed = master_options[p][choice][key2];
                        for (let opt of el2.options) {
                            if(!allowed.includes(opt.value)) {
                                opt.classList.add("unavailable");
                            }
                        }
                    }
                    catch(e) {
                        if(e instanceof TypeError || e instanceof ReferenceError)
                            console.log("Did not find an element with name calc_" + key2);
                        else
                            console.log("Expected error while accessing calc_" + key2 + ": " + String(e))
                    }
                }
            }
            if (p in master_available && choice in master_available[p]) {
                for (ind=0; ind<list_available_elements.length; ind++) {
                    pname = list_available_elements[ind];
                    try {
                        el2 = $(target).find("#calc_"+pname);
                        {% if is_batch %}
                        row = $(target).find("#row_"+pname);
                        {% endif %}
                        if(el2 != undefined) {
                            if(!master_available[p][choice].includes(pname)) {
                                el2.addClass("unavailable");
                                {% if is_batch %}
                                row.addClass("unavailable");
                                {% endif %}
                            }
                        }
                    }
                    catch(e) {
                        if(e instanceof TypeError || e instanceof ReferenceError)
                            console.log("Did not find an element with name calc_" + pname);
                        else
                            console.log("Expected error while accessing calc_" + pname + ": " + String(e))
                    }
 
                }
            }
        }
    });

    try {
        software = $(context).find("[name='calc_software']").value;
        if(software == "Gaussian") {
            $(target).find(".scan_from").each(function(ind) {
                if(!$(this).hasClass("unavailable")) {
                    $(this).addClass("unavailable");
                }
            });
        }
    }
    catch (excp) {
        console.log("No software element found.")
    }
    set_availables(context, target);

    /* hide columns with hidden content */
    $(target).find(".column.optional-column").each(function(ind) {
        if($(this).children("div:not(.unavailable)").length == 0) {
            {% if is_batch %}
            $(this).parent().hide();
            {% else %}
            $(this).hide();
            {% endif %}
        }
        else {
            {% if is_batch %}
            $(this).parent().show();
            {% else %}
            $(this).show();
            {% endif %}
        }

    });

    {% if is_batch %}
    for (ind=0; ind<parameters_dependencies.length; ind++) {
        let key=parameters_dependencies[ind]
        el = $(target).find("[name='" + key + "']");
        el.removeAttr("disabled");
        for (const dep_key in parameters_dependencies[key]) {
            set = $(context).find("[name='" + parameters_dependencies[key][dep_key] + "']").prop("checked");
            if(!set) {
                el.attr("disabled", true);
                break;
            }
        }

    }
    {% endif %}
}

function set_availables(context, target) {
    $(target).find('select').each(function() {
        sel = $(this).find("option.unavailable:selected");
        sel2 = $(this).find("option:selected")
        if(sel.length != 0 || sel2.length == 0) {
            opt = $(this).find("option:not(.unavailable):not(:disabled)");
            $(this).val(opt.val());
        }
    });
}

