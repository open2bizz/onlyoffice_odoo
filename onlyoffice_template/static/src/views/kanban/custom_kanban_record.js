/** @odoo-module **/
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

export class CustomKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    getCreationDate() {
        const creationTimestamp = this.props.record.data?.create_date?.ts;
        return creationTimestamp ? new Date(creationTimestamp).toLocaleDateString() : "";
    }

    async editTemplate() {
        this.env.bus.trigger("edit-template", this.props.record.data);
    }

    async deleteTemplate() {
        this.dialog.add(ConfirmationDialog, {
            body: this.env._t("Are you sure you want to delete this template?"),
            confirm: async () => {
                try {
                    await this.orm.call(
                        "onlyoffice.template",
                        "action_delete_attachment",
                        [this.props.record.data.id]
                    );
                    this.props.record.model.load();
                    this.props.record.model.notify();
                } catch (error) {
                    console.error("Error deleting template:", error);
                }
            }
        });
    }
}

CustomKanbanRecord.template = "onlyoffice_template.CustomKanbanRecord";