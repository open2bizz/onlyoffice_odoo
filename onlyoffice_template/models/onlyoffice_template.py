from odoo import api, models, fields
from odoo.exceptions import UserError
import json
import re

class OnlyOfficeTemplate(models.Model):
    _name = 'onlyoffice.template'
    _description = 'ONLYOFFICE Template'

    name = fields.Char(required=True, string="Template Name")
    file = fields.Binary()
    creator_id = fields.Many2one('res.users', readonly=True, string="Creator")
    creation_date = fields.Datetime("Creation Date", readonly=True)
    attachment_id = fields.Many2one('ir.attachment', readonly=True)
    mimetype = fields.Char(default='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    models = fields.Selection([
        ('sale.order', 'Sale Order'),
        ('res.partner', 'Partner'),
    ], string='Applicable Models', required=True)

    @api.model
    def create(self, vals):
        if 'file' in vals:
            vals['attachment_id'] = self._create_attachment(vals).id
        return super(OnlyOfficeTemplate, self).create(vals)

    def _create_attachment(self, vals):
        return self.env['ir.attachment'].create({
            'name': vals.get('name'),
            'mimetype': vals.get('mimetype', self.mimetype),
            'datas': vals['file'],
            'res_model': self._name,
            'res_id': self.id,
        })

    @api.model
    def get_fields_for_model(self, model_name='sale.order'):
        models_fields_info = {}
        fields_info = self.env[model_name].fields_get()

        for field_name, field_props in fields_info.items():
            field_type = field_props['type']
            models_fields_info.setdefault(model_name, {})[field_name] = {
                'name': field_name,
                'string': field_props['string'],
                'type': field_type,
            }

            if field_type == 'one2many':
                self._add_related_fields(models_fields_info, field_props)

        return json.dumps(models_fields_info, ensure_ascii=False)

    def _add_related_fields(self, models_fields_info, field_props):
        related_model_name = field_props['relation']
        related_fields_info = self.env[related_model_name].fields_get()

        models_fields_info[related_model_name] = {
            related_field: {
                'name': related_field,
                'string': related_fields_info[related_field]['string'],
                'type': related_fields_info[related_field]['type']
            } for related_field in related_fields_info
        }

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