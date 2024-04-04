from odoo import api, models, fields
from odoo.exceptions import UserError
import json
import re

class OnlyofficeTemplate(models.Model):
    _name = 'onlyoffice.template'
    _description = 'ONLYOFFICE Template'

    name = fields.Char(required=True, string="Template Name")
    file = fields.Binary()
    create_uid = fields.Many2one('res.users', readonly=True)
    create_date = fields.Datetime("Template Create Date", readonly=True)
    attachment_id = fields.Many2one('ir.attachment', readonly=True)
    mimetype = fields.Char(default='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    models = fields.Selection([
        ('sale.order', 'Sale Order'),
        ('res.partner', 'Partner'),
    ], string='Models', required=True)

    @api.model
    def create(self, vals):
        record = super(OnlyofficeTemplate, self).create(vals)
        if vals.get('file'):
            attachment = self.env['ir.attachment'].create({
                'name': record.name,
                'mimetype': vals['mimetype'],
                'datas': vals['file'],
                'res_model': self._name,
                'res_id': record.id,
            })
            record.attachment_id = attachment.id
        return record

    @api.model
    def upload(self, vals):
        record = super(OnlyofficeTemplate, self).create(vals)
        if vals.get('file'):
            attachment = self.env['ir.attachment'].create({
                'name': record.name,
                'mimetype': vals['mimetype'],
                'datas': vals['file'],
                'res_model': self._name,
                'res_id': record.id,
            })
            record.attachment_id = attachment.id
        return record

    @api.model
    def get_fields(self):
        model_name = "sale.order"
        
        models_fields_info = {}
        fields_info = self.env[model_name].fields_get()

        for field_name, field_props in fields_info.items():
            field_type = field_props['type']
            
            models_fields_info.setdefault(model_name, {})[field_name] = {
                'name': field_name,
                'string': field_props['string'],
                'type': field_type
            }
            
            # Если поле типа one2many, также получаем информацию о связанных полях
            if field_type == 'one2many':
                related_model_name = field_props['relation']
                related_fields_info = self.env[related_model_name].fields_get()
                
                models_fields_info[related_model_name] = {
                    related_field: {
                        'name': related_field,
                        'string': related_fields_info[related_field]['string'],
                        'type': related_fields_info[related_field]['type']
                    } for related_field in related_fields_info
                }

        return json.dumps(models_fields_info, ensure_ascii=False)

    def action_delete_attachment(self):
        self.ensure_one()
        try:
            if self.attachment_id:
                self.attachment_id.unlink()
            self.attachment_id = False
            self.file = False
            self.sudo().unlink()
        except Exception as e:
            raise UserError("Error on delete:" , str(e))
        return

    def unlink(self):
        for record in self:
            if record.attachment_id:
                record.attachment_id.unlink()
        return super(OnlyofficeTemplate, self).unlink()