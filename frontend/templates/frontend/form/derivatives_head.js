function calc_deriv_changed(checkbox) {
    list = document.getElementById("calc_list_derivatives");
    if(checkbox.checked) {
        list.style.display = "block";
    }
    else {
        list.style.display = "none";
    }
    refresh_availabilities();
}
