document.addEventListener('DOMContentLoaded', () => {

    // Handle toggle between Inferred/Asserted
    const toggle = document.getElementById('toggle-inferred');
    toggle.addEventListener('change', async () => {
        window.isInferred = toggle.checked;
        await reloadTree();
        clearDetails();
    });

    // Delegate clicks on tree nodes
    document.getElementById('sidebar').addEventListener('click', (e) => {
        const element = e.target.closest('.node-content');
        if (!element) return;

        e.stopPropagation();

        const nodeId = element.dataset.id;

        // Toggle selection
        document.querySelectorAll('.node-content').forEach(el => el.classList.remove('active'));
        element.classList.add('active');

        loadDetails(nodeId);

        // Expand / Collapse
        const treeNode = element.parentElement;
        const childrenContainer = treeNode.querySelector(':scope > .children-container');
        const expander = element.querySelector('.expander');
        if (childrenContainer) {
            const expanded = childrenContainer.classList.toggle('expanded');
            expander?.classList.toggle('open', expanded);
        }
    });
});

// Reload tree from backend when inferred/ asserted changes
async function reloadTree() {
    const inferredParam = window.isInferred ? 'true' : 'false';
    const response = await fetch(`/navigation/?inferred=${inferredParam}`);
    const htmlText = await response.text();

    // Extract the tree-root HTML from the response
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = htmlText;
    const newTreeRoot = tempDiv.querySelector('.tree-root');
    const currentTreeRoot = document.querySelector('.tree-root');
    if (newTreeRoot && currentTreeRoot) {
        currentTreeRoot.replaceWith(newTreeRoot);
    }
}

// Clear the details panel
function clearDetails() {
    const contentArea = document.getElementById('details-area');
    contentArea.innerHTML = '<div style="display:flex; align-items:center; justify-content:center; height:100%; opacity:0.3;"><p>Select a node to view details</p></div>';
}

// Load node details
async function loadDetails(nodeId) {
    const contentArea = document.getElementById('details-area');
    contentArea.innerHTML = '<div style="color:var(--text-color); opacity:0.5;">Loading...</div>';

    try {
        const inferredParam = window.isInferred ? '&inferred=true' : '';
        const response = await fetch(`/details/?id=${encodeURIComponent(nodeId)}${inferredParam}`);
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

// Render details panel
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
    const describeUrl = `/sparql/?run=true&query=DESCRIBE <${data.id}>${window.isInferred ? '&inferred=true' : ''}`;

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
