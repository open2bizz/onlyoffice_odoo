/** @odoo-module **/
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useService } from "@web/core/utils/hooks";
import { _t } from "web.core";
import { CustomKanbanDialog } from "./custom_kanban_dialog"

const { useState } = owl;

export class CustomKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.notificationService = useService("notification");

        this.state = useState({
            fields: {},
            isEditorVisible: false
        });

        this.env.bus.on('edit-template', this, (data) => this.handleTemplateEdit(data));
    }

    async handleTemplateEdit(data) {
        await this.openTemplateEditor(data.attachment_id[0]);
    }

    /*
        char //text
        text //multiline text
        integer
        float
        monetary
        html
        date
        datetime
        boolean //Checkbox
        selection //dropbox
        binary //file, image, sign
        many2one
        one2many
        many2many
    */
    async onFieldElementClicked(_event, field) {
        const data = {
            model: field.model,
            name: field.name,
            string: field.string,
            type: field.type
        }
        const iframe = document.querySelector("iframe");
        iframe.contentWindow.postMessage(data, window.location.origin);
    }

    async onTemplateCreationButtonClick() {
        this.env.services.dialog.add(CustomKanbanDialog, {
            resModel: 'onlyoffice.template',
            title: this.env._t("Create"),
            onSave: async (record) => {
                console.log(record)
                const result = await this.rpc(`/onlyoffice/template/create`);
                if (result.error) {
                    this.notificationService.add(result.error, {type: "error", sticky: false}); 
                } else {
                    this.notificationService.add(_t("New template created in Documents"), {type: "info", sticky: false});
                    //await this.openTemplateEditor(result.file_id);
                }
                this.model.load();
                this.model.notify();
            },
         });
    }

    async generateFieldsList() {
        try {
            const models = JSON.parse(await this.orm.call("onlyoffice.template", "get_fields_for_model", []));
            const array = [];
            let i = 0;
            Object.keys(models).forEach(model => {
                const fields = models[model];
                Object.keys(fields).forEach(fieldName => {
                    const field = fields[fieldName];
                    array.push({
                        model: model,
                        name: field.name,
                        string: field.string,
                        type: field.type,
                        key: i
                    });
                    i++;
                });
            });
            this.state.fields = array;
        } catch (error) {
            console.error("RPC Error:", error);
        }
    }

    embedIframe(id) {
        const iframeContainer = document.querySelector(".iframe");
        iframeContainer.innerHTML = `<iframe src="/onlyoffice/editor/${id}" frameborder="0" style="width:100%; height:100%;"></iframe>`;
    }

    async openTemplateEditor(id) {
        if (!this.state.isEditorVisible) {
            await this.generateFieldsList();
            this.embedIframe(id);
            this.state.isEditorVisible = true;
        }
    }
}

CustomKanbanController.template = "onlyoffice_template.CustomKanbanController";