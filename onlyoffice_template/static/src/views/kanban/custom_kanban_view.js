/** @odoo-module */
import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { CustomKanbanController } from "./custom_kanban_controller";
import { CustomKanbanRenderer } from "./custom_kanban_renderer";

export const customKanbanView = {
    ...kanbanView,
    Controller: CustomKanbanController,
    Renderer: CustomKanbanRenderer,
    buttonTemplate: "onlyoffice_template.CustomKanbanController.Buttons",
};

registry.category("views").add("custom_kanban", customKanbanView);