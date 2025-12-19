document.addEventListener('DOMContentLoaded', () => {
    // Handling tree expansion
    document.querySelectorAll('.node-content').forEach(element => {
        element.addEventListener('click', (e) => {
            e.stopPropagation();

            // Toggle selection
            document.querySelectorAll('.node-content').forEach(el => el.classList.remove('active'));
            element.classList.add('active');

            // Load details
            const nodeId = element.dataset.id;
            loadDetails(nodeId);

            // Expand/Collapse if it has children
            const parentLi = element.parentElement;
            const childrenContainer = parentLi.querySelector('.children-container');
            const expander = element.querySelector('.expander');

            if (childrenContainer) {
                const isExpanded = childrenContainer.classList.contains('expanded');
                if (isExpanded) {
                    childrenContainer.classList.remove('expanded');
                    if (expander) expander.classList.remove('open');
                } else {
                    childrenContainer.classList.add('expanded');
                    if (expander) expander.classList.add('open');
                }
            }
        });
    });
});

async function loadDetails(nodeId) {
    const contentArea = document.getElementById('details-area');
    contentArea.innerHTML = '<div style="color:var(--text-color); opacity:0.5;">Loading...</div>';

    try {
        const response = await fetch(`/details/?id=${encodeURIComponent(nodeId)}`);
        const data = await response.json();

        if (data.error) {
            contentArea.innerHTML = `<div style="color:red">Error: ${data.error}</div>`;
            return;
        }

        renderDetails(data);
    } catch (e) {
        console.error(e);
        contentArea.innerHTML = '<div style="color:red">Failed to load details.</div>';
    }
}

function renderDetails(data) {
    const contentArea = document.getElementById('details-area');

    let propertiesHtml = data.properties.map(p => {
        const label = p.predicate_label || p.predicate.split('#').pop().split('/').pop();

        let valueHtml;
        if (p.is_uri) {
            const displayValue = p.object_label || p.object.split('#').pop().split('/').pop();
            valueHtml = `<a href="#" class="uri-link" onclick="loadDetails('${p.object}')">${displayValue}</a> <span style="font-size:0.8em; opacity:0.5">(${p.object})</span>`;
        } else {
            valueHtml = p.object_label || p.object;
        }

        return `
            <div class="property-row">
                <div class="property-label">${label}</div>
                <div class="property-value">${valueHtml}</div>
            </div>
        `;
    }).join('');

    const title = data.id.split('#').pop();
    const encodedId = encodeURIComponent(data.id);
    const describeUrl = `/sparql/?run=true&query=DESCRIBE <${data.id}>`; // No component encoding for URI structure components

    contentArea.innerHTML = `
        <div class="details-card">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <h2>${title}</h2>
                <a href="${describeUrl}" class="action-btn">Describe Axiom</a>
            </div>
            <div style="margin-bottom: 20px; font-family: monospace; opacity: 0.6; font-size: 0.9em;">
                ${data.id}
            </div>
            <div class="properties">
                ${propertiesHtml}
            </div>
        </div>
    `;
}
