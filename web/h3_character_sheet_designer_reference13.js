import {app} from '../../scripts/app.js';
import {api} from '../../scripts/api.js';
import {createExtension} from './reference13_integration.js';
app.registerExtension(createExtension(app, api));
