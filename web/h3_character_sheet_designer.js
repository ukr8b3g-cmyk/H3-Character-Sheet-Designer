import {app} from '../../scripts/app.js';
import {api} from '../../scripts/api.js';
import {createExtension} from './integration.js';
app.registerExtension(createExtension(app, api));
