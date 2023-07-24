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
