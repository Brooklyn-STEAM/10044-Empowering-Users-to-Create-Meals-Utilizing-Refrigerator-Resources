
function checkAll(category) {
    let inputs = document.getElementsByClassName(category)
   
    for (let i = 0; i < inputs.length ; i++){
        let checkbox = document.getElementById(inputs[i].id);
        checkbox.checked = !checkbox.checked;
    }

    
}