
document.addEventListener("DOMContentLoaded", function() {
    let logsTable = $("#datatables-reponsive").DataTable({
        // "responsive": true,
        "destroy": true,
        "searching": false,
        "scrollX": true,
        "paging":   true,
        "ordering": false,
        "info":     false,
    });            
});