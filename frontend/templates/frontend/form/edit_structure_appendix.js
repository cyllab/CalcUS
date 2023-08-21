$('.element').click(function() {
    let cmd = $(this).attr('data-el');
    $('.element.is-primary').removeClass("is-primary");

    reset_mode();

    switch(cmd)
    {
        case 'x':
            Jmol.script(editor, 'set atomPicking on');
            Jmol.script(editor, 'set picking deleteAtom');
            break;
        default:
            Jmol.script(editor, 'set atomPicking on');
            Jmol.script(editor, 'set picking select atom');
            Jmol.script(editor, 'set picking dragMinimize');
            Jmol.script(editor, 'set picking assignAtom_'+cmd);
            $(this).addClass('is-primary');
    }

    return false;
});

$('.bond').click(function() {
    let bondtype = $(this).attr('data-bond');
    $('.bond.is-primary').removeClass("is-primary");
    $(this).addClass('is-primary');
    // unhighlight the chosen action?
    reset_mode();
    Jmol.script(editor, 'set picking assignBond_' + bondtype);
    return false;
});


$('.action').click(function() {
    let cmd = $(this).attr('data-action');
    if(cmd != "del-sel" && cmd != "deselect-all") {
        $('.action.is-primary').removeClass("is-primary");
        $(this).addClass('is-primary');
        $("#actions_cheatsheet").find(".cheatsheet").hide(); 
        $("#cheatsheet_" + cmd).show();
        reset_mode()    
    }


    switch(cmd)
    {
        case 'browse':
            Jmol.script(editor, 'set pickingStyle select toggle');
            break;
        case 'rotate':
            Jmol.script(editor, 'set allowRotateSelected true');
            Jmol.script(editor, 'set atomPicking on');
            Jmol.script(editor, 'set picking dragMolecule');
            Jmol.script(editor, 'set picking rotateBond');
            break;
        case 'drag-atom':
            Jmol.script(editor, 'set atomPicking on');
            Jmol.script(editor, 'set picking dragAtom');
            break;
        case 'drag-mol':
            Jmol.script(editor, 'set atomPicking on');
            Jmol.script(editor, 'set picking dragMolecule');
            break;
        case 'select':
            Jmol.script(editor, 'set atomPicking on');
            Jmol.script(editor, 'set pickingStyle select drag');
            Jmol.script(editor, 'set picking select atom');
            break;
        case 'del-sel':
            Jmol.script(editor, 'delete selected');
            break
        case 'deselect-all':
            Jmol.script(editor, 'select none');
            break;

        default:
            return
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


$('#jsmol_done').click(function() {
    modalEdit.style.display = "none";
    let struct_mol = Jmol.getPropertyAsString(editor, "extractModel", "all");
    let mol_read = ChemDoodle.readMOL(struct_mol, 1);
    ChemDoodle.relabel(mol_read);
    viewer.loadMolecule(mol_read);	

    sketcher.loadMolecule(ChemDoodle.readMOL(struct_mol));

    return false;
});


