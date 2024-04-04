/** @odoo-module **/
import { FormController } from "@web/views/form/form_controller";
import { TemplateFillDialog } from "./template_fill_dialog";

export class CustomFormController extends FormController {
    openTemplateFillDialog() {
        this.env.services.dialog.add(TemplateFillDialog, {
            formControllerProps: this.props
        });
    }
}

CustomFormController.template = "onlyoffice_template.CustomFormController";
