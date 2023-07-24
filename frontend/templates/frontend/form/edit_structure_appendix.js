var atomBtns = $('.element');
atomBtns.click(function() {
    let cmd = $(this).attr('data-el');
    $('.element.is-primary').removeClass("is-primary");

    switch(cmd)
    {
        case 'x':
            Jmol.script(editor, 'set picking deleteAtom');
            Jmol.script(editor, 'set atomPicking on');
            break;
        case 'off':/// to use
            Jmol.script(editor, 'set atomPicking off');
            break;
        case 'dra':

            Jmol.script(editor, 'set atomPicking on');
            Jmol.script(editor, 'set picking dragMinimize'); // on off
            $(this).addClass('is-primary');
            break;
        default:
            Jmol.script(editor, 'set atomPicking on');
            Jmol.script(editor, 'set picking dragMinimize');
            Jmol.script(editor, 'set picking assignAtom_'+cmd);
            $(this).addClass('is-primary');
    }

    return false;
});

var modalEdit = document.getElementById("edit_structure_modal");
var modalBtnEdit = document.getElementById("edit_button");
if(modalBtnEdit) {
    modalBtnEdit.onclick = function(){
        modalEdit.style.display = "block";
    }
    closeBtnBs.onclick = function(){
        modalEdit.style.display = "none";
    }
}

var bondBtns = $('.bond');
bondBtns.click(function() {
    let bondtype = $(this).attr('data-bond');
    $('.bond.is-primary').removeClass("is-primary");
    $(this).addClass('is-primary');
    Jmol.script(editor, 'set picking assignBond_' + bondtype);
    return false;
});

var doneBtn = $('#jsmol_done');
doneBtn.click(function() {
    modalEdit.style.display = "none";
    let struct_mol = Jmol.getPropertyAsString(editor, "extractModel", "all");
    let mol_read = ChemDoodle.readMOL(struct_mol, 1);
    ChemDoodle.relabel(mol_read);
    viewer.loadMolecule(mol_read);	

    sketcher.loadMolecule(ChemDoodle.readMOL(struct_mol));

    return false;
});


