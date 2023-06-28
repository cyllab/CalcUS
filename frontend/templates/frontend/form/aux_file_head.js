function refresh_aux_mol() {
    proj = document.getElementById("calc_project");
    $.ajax({
        headers: {
            "X-CSRFToken": '{{ csrf_token }}',
        },

        type: "POST", 
        data: {
            'proj': proj.value,
        },
        url: "/aux_molecule/",
        success: function (response) { 
            $("#aux_mol").html(response);
            refresh_aux_ensemble();	
        }
    });
}
function refresh_aux_ensemble() {
    aux_mol = document.getElementById("aux_mol");
    $.ajax({
        headers: {
            "X-CSRFToken": '{{ csrf_token }}',
        },

        type: "POST", 
        data: {
            'mol_id': aux_mol.value,
        },
        url: "/aux_ensemble/",
        success: function (response) { 
            $("#aux_ensemble").html(response);
            refresh_aux_structure();	
        }
    });
}
function refresh_aux_structure() {
    aux_mol = document.getElementById("aux_ensemble");
    $.ajax({
        headers: {
            "X-CSRFToken": '{{ csrf_token }}',
        },

        type: "POST", 
        data: {
            'e_id': aux_ensemble.value,
        },
        url: "/aux_structure/",
        success: function (response) { 
            $("#aux_struct").html(response);
        }
    });
    
}
