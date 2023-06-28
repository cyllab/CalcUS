function save_preset() {
    preset_name = prompt("Name of the preset?", "")
    if(preset_name != null) {
        data = $("#calcform").serializeArray();
        data.push({ name: 'preset_name', value: preset_name});
        $.ajax({
            data: data, 
            headers: {
                "X-CSRFToken": '{{ csrf_token }}',
            },

            type: "POST", 
            url: "/save_preset/",
            success: function (response) { 
                $("#preset_msg").html(response);
                refresh_presets();
            }
        });
    }

}

function load_selected_preset() {
    preset = document.getElementById("presets").value;
    load_preset(preset);
}
function delete_preset() {
    preset = document.getElementById("presets").value;
    $.ajax({
        headers: {
            "X-CSRFToken": '{{ csrf_token }}',
        },

        type: "POST", 
        url: "/delete_preset/" + preset,
        success: function (response) { 
            $("#preset_msg").html(response);
            refresh_presets();
        }
    });

}

function refresh_presets() {
    $("#presets").load("/presets/");
}

function load_preset(id) {
    if(id == undefined) {
        return;
    }
    $.ajax({
        method: "POST",
        url: "/load_preset/" + id,
        headers: {
            "X-CSRFToken": '{{ csrf_token }}',
        },
        success: function(data) {
            eval(data);
            refresh_availabilities();
            check("functional");
            check("basis_set");
            check("solvent");
            refresh_availabilities();
        },
    });
}
