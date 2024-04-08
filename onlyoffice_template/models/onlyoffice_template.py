from odoo import api, models, fields
from odoo.exceptions import UserError
import json
import re

class OnlyOfficeTemplate(models.Model):
    _name = 'onlyoffice.template'
    _description = 'ONLYOFFICE Template'

    name = fields.Char(required=True, string="Template Name")
    file = fields.Binary(string="Upload an existing template")
    creator_id = fields.Many2one('res.users', readonly=True, string="Creator")
    creation_date = fields.Datetime("Creation Date", readonly=True)
    attachment_id = fields.Many2one('ir.attachment', readonly=True)
    mimetype = fields.Char(default='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    model = fields.Selection([
        ('sale.order', 'Sale Order'),
        ('res.partner', 'Partner'),
    ], string='Applicable Models', required=True)

    @api.model
    def create(self, vals):
        datas = vals.pop('file', None)
        record = super(OnlyOfficeTemplate, self).create(vals)
        if datas:
            attachment = self.env['ir.attachment'].create({
                'name': vals.get('name', record.name),
                'mimetype': vals.get('mimetype', ''),
                'datas': datas,
                'res_model': self._name,
                'res_id': record.id,
            })
            record.attachment_id = attachment.id
        return record

    @api.model
    def get_fields_for_model(self, model_name):
        processed_models = set()
        models_info_list = []

        def process_model(name):
            if name in processed_models:
                return
            processed_models.add(name)

            model_info = {'name': name, 'fields': []}
            fields_info = self.env[name].fields_get()

            for field_name, field_props in fields_info.items():
                field_type = field_props['type']
                field_detail = {
                    'name': field_name,
                    'string': field_props['string'],
                    'type': field_type,
                }
                model_info['fields'].append(field_detail)

                if field_type == 'one2many':
                    related_model_name = field_props['relation']
                    process_model(related_model_name)

            models_info_list.append(model_info)

        process_model(model_name)
        return json.dumps(models_info_list, ensure_ascii=False)

    def action_delete_attachment(self):
        self.ensure_one()
        if self.attachment_id:
            self.attachment_id.unlink()
        self.unlink()

    def unlink(self):
        attachments = self.mapped('attachment_id')
        if attachments:
            attachments.unlink()
        return super(OnlyOfficeTemplate, self).unlink()