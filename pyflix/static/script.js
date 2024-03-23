// drag n drop doesnt work on mobile.
document.addEventListener('DOMContentLoaded', function() {
    let dragSrcEl = null;

    function handleDragStart(e) {
        if (this.getAttribute('draggable') === 'true') {
            dragSrcEl = this;
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/html', this.outerHTML);
            this.classList.add('dragging');
        } else {
            e.preventDefault(); // prevent drag start for non-movable items.
        }
    }

    function handleDragOver(e) {
        if (e.preventDefault) {
            e.preventDefault(); // necessary. Allows us to drop.
        }
        e.dataTransfer.dropEffect = 'move';  
        return false;
    }

    function handleDragEnter(e) {
        if (this.getAttribute('draggable') === 'true') {
            this.classList.add('over');
        }
    }

    function handleDragLeave(e) {
        this.classList.remove('over');  
    }

    function handleDrop(e) {
        if (e.stopPropagation) {
            e.stopPropagation(); // stops the browser from redirecting.
        }

        if (dragSrcEl !== this) {
            this.parentNode.removeChild(dragSrcEl);
            const dropHTML = e.dataTransfer.getData('text/html');
            this.insertAdjacentHTML('beforebegin', dropHTML);
            const dropElem = this.previousSibling;
            addDnDEvents(dropElem);

            updateQualityOrderInputs();
        }
        this.classList.remove('over');
        return false;
    }

    function handleDragEnd(e) {
        this.classList.remove('dragging');
    }

    function addDnDEvents(elem) {
        elem.addEventListener('dragstart', handleDragStart, false);
        elem.addEventListener('dragenter', handleDragEnter, false);
        elem.addEventListener('dragover', handleDragOver, false);
        elem.addEventListener('dragleave', handleDragLeave, false);
        elem.addEventListener('drop', handleDrop, false);
        elem.addEventListener('dragend', handleDragEnd, false);
    }

    function updateQualityOrderInputs() {
        document.querySelectorAll('input[name="quality_order[]"]').forEach(input => input.remove());
        document.querySelectorAll('#quality_order .drag-item[draggable="true"]').forEach((item, index) => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'quality_order[]';
            input.value = item.textContent.trim();
            document.querySelector('form').appendChild(input);
        });
    }

    async function saveConfigAndOpenStremio() {
        const formData = new FormData(document.querySelector('form'));
        try {
            const response = await fetch('/configure', {
                method: 'POST',
                body: formData,
            });
            if (!response.ok) throw new Error('Network response was not ok');
            var manifestUrl = `stremio://${window.location.host}/manifest.json`;
            window.location.href = manifestUrl;
        } catch (error) {
            console.error('Failed to save configuration:', error);
            alert('Failed to save configuration.');
        }
    }

    document.querySelector('form').addEventListener('submit', function(event) {
        event.preventDefault();
        saveConfigAndOpenStremio();
    });

    let items = document.querySelectorAll('#quality_order .drag-item');
    items.forEach(addDnDEvents);
});



