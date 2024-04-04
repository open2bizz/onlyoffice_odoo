/** @odoo-module **/

import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

export class CustomKanbanDialog extends FormViewDialog {
    setup() {
        super.setup();
        if (this.props.onSave) {
            this.viewProps.saveRecord = this.props.onSave;
        }
    }
}
CustomKanbanDialog.props = {
    ...FormViewDialog.props,
    onSave: { type: Function, optional: true }
};