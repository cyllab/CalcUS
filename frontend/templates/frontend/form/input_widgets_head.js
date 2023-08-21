function load_nih(btn) {
    $(btn).addClass("is-loading");
    let name = document.getElementById("nih_name").value;
    $.ajax({
        method: "POST",
        url: "https://cactus.nci.nih.gov/chemical/structure/" + name + "//file?format=mol"
    }).success(function(data) {
        let mol_read = ChemDoodle.readMOL(data, multiplier=1);
        ChemDoodle.relabel(mol_read);
        viewer.clear();
        viewer.loadMolecule(mol_read);	
        sketcher.clear();
        sketcher.loadMolecule(ChemDoodle.readMOL(data));	
        sketcher.center();
        Jmol.script(editor, 'load inline "' + data + '"');
        $("#calc_mol_name").val(name);
        $("#nih_msg").text("");
    }).fail(function(data) {
        $("#nih_msg").text("Sorry, could not find " + name);
    }).always(function() {
        $(btn).removeClass("is-loading");
    });
}

function add_3D() {
    let mol = ChemDoodle.writeMOL(sketcher.getMolecule());
    document.getElementById("add_3D_btn").classList.add("is-loading");
    $.ajax({
        method: "POST",	 	 
        url: "/gen_3D/",
        headers: {
            "X-CSRFToken": '{{ csrf_token }}',
        },

        data: {'mol': mol},
        statusCode: {
            404: function(data) {
                $("#3d_msg").html("Error while generating structure");
            },
            200: function(data) {
                $("#3d_msg").html("");
                let mol_read = ChemDoodle.readXYZ(data);
                ChemDoodle.relabel(mol_read);
                viewer.addMolecule(mol_read);	
                document.getElementById("add_3D_btn").classList.remove("is-loading");
                
                Jmol.script(editor, 'load APPEND inline "' + data + '"');
            }
        }
    }).always(function() {
        document.getElementById("gen_3D_btn").classList.remove("is-loading");
    });

}
