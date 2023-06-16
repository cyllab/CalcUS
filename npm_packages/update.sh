#!/bin/bash

npm run build-bulma

cp css-dist/bulma.min.css ../static/frontend/

cp node_modules/jquery/dist/jquery.min.js ../static/frontend/
cp node_modules/3dmol/build/3Dmol-min.js ../static/frontend/
cp node_modules/3dmol/build/3Dmol.ui-min.js ../static/frontend/
cp node_modules/bulma-slider/dist/js/bulma-slider.min.js ../static/frontend/
cp node_modules/clipboard/dist/clipboard.min.js ../static/frontend/

cp node_modules/cytoscape/dist/cytoscape.min.js ../static/frontend/
cp node_modules/cytoscape-dagre/cytoscape-dagre.js ../static/frontend/
cp node_modules/dagre/dist/dagre.min.js ../static/frontend/

cp node_modules/dygraphs/dist/dygraph.min.css ../static/frontend/
cp node_modules/dygraphs/dist/dygraph.min.js ../static/frontend/

cp node_modules/jquery-ui/dist/jquery-ui.min.js ../static/frontend/
cp node_modules/jquery-ui/dist/themes/base/jquery-ui.min.css ../static/frontend/

cp node_modules/shepherd.js/dist/css/shepherd.css ../static/frontend/
cp node_modules/shepherd.js/dist/js/shepherd.min.js ../static/frontend/
cp node_modules/@floating-ui/core/dist/floating-ui.core.umd.min.js ../static/frontend/
cp node_modules/@floating-ui/dom/dist/floating-ui.dom.umd.min.js ../static/frontend/

