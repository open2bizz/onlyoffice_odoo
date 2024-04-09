# -*- coding: utf-8 -*-

#
# (c) Copyright Ascensio System SIA 2023
#

from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.tools import file_open
from odoo.tools.translate import _

from odoo.addons.onlyoffice_odoo.utils import file_utils, jwt_utils, config_utils

import base64
import requests
import json
from datetime import datetime, date
from urllib.request import urlopen

class OnlyofficeTemplate_Connector(http.Controller):
    @http.route("/onlyoffice/template/create", auth="user", methods=["POST"], type="json")
    def create_template(self, data):
        file_data = data.get('file') or base64.encodebytes(file_utils.get_default_file_template(request.env.user.lang, "docx"))
        mimetype = file_utils.get_mime_by_ext("docx")

        attachment = request.env['onlyoffice.template'].create({
            "name": data['name'] + ".docxf",
            "model": data['model'],
            "file": file_data,
            "mimetype": mimetype
        })
        
        return {"file_id": attachment.attachment_id.id}
    
    @http.route("/onlyoffice/template/upload", auth="user", methods=["POST"], type="json")
    def upload(self, url, title):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            if response.status_code != 200:
                raise Exception("HTTP error", response.status_code)
            if 'Content-Length' not in response.headers:
                raise Exception("Empty file")
            if not response.headers['Content-Type']:
                raise Exception("Unknown content type")

            data = urlopen(url).read()
            attachment = request.env['onlyoffice.template'].create({
                "name": title,
                "file": base64.encodebytes(data),
                "mimetype": response.headers['Content-Type'],
            })
            
            return {'ids': attachment.id}

        except Exception as e:
            raise Exception("Error: ", str(e))
    
    @http.route("/onlyoffice/template/fill", auth="user", methods=["POST"], type="json")
    def fill_template(self, template_id, record_id, model_name):
        jwt_secret=config_utils.get_jwt_secret(request.env)
        jwt_header=config_utils.get_jwt_header(request.env)
        odoo_url = config_utils.get_odoo_url(request.env)
        docserver_url = config_utils.get_doc_server_public_url(request.env)

        template_attachment_id = http.request.env["onlyoffice.template"].browse(template_id).attachment_id.id

        oo_security_token = jwt_utils.encode_payload(request.env, { "id": request.env.user.id }, config_utils.get_internal_jwt_secret(request.env))

        data_url = odoo_url + "onlyoffice/template/callback/fill"
        data_url_with_params = f"{data_url}?template_attachment_id={template_attachment_id}&model_name={model_name}&record_id={record_id}&oo_security_token={oo_security_token}"
        data = {
            "async": False,
            "url": data_url_with_params
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if bool(jwt_secret):
            payload = {"payload": data}
            header_token = jwt_utils.encode_payload(request.env, payload, jwt_secret)
            headers[jwt_header] = "Bearer " + header_token
            token = jwt_utils.encode_payload(request.env, data, jwt_secret)
            data["token"] = token

        request_url = docserver_url + "docbuilder"
        response = requests.post(request_url, data=json.dumps(data), headers = headers)
        
        response_json = json.loads(response.text)

        urls = response_json.get('urls')
        if urls:
            first_url = next(iter(urls.values()), None)
            if first_url:
                return {'href': first_url}

        error_code = response_json.get('error')
        if error_code:
            error_messages = {
                -1: "Unknown error.",
                -2: "Generation timeout error.",
                -3: "Document generation error.",
                -4: "Error while downloading the document file to be generated.",
                -6: "Error while accessing the document generation result database.",
                -8: "Invalid token."
            }
            return {'error': error_messages.get(error_code, "Error code not recognized.")}

        return {'error': "Unknown error"}
    
    @http.route("/onlyoffice/template/callback/fill", auth="public")
    def template_callback(self, template_attachment_id, model_name, record_id, oo_security_token=None):
        record_id = int(record_id)
        record = http.request.env[model_name].sudo().browse(record_id)
        record_values = record.read()[0]

        non_array_items = []
        array_items = []
        markup_items = []

        def get_related_values(submodel_name, record_ids, depth=0):
            if depth > 3:
                return []
            records = http.request.env[submodel_name].sudo().browse(record_ids)
            result = []
            for record in records:
                record_values = record.read()[0]
                processed_record = {}
                for key, value in record_values.items():
                    field_dict = {}
                    if isinstance(value, bytes):
                        continue
                    elif hasattr(value, '__html__'):
                        field_dict[f"{submodel_name}_{key}"] = str(value)
                        markup_items.append(field_dict)
                    elif isinstance(value, list) and value and http.request.env[submodel_name]._fields[key].type == 'one2many':
                        related_model = http.request.env[submodel_name]._fields[key].comodel_name
                        processed_record[key] = get_related_values(related_model, value, depth + 1)
                    elif isinstance(value, tuple) and len(value) == 2:
                        processed_record[key] = value[1]
                    elif isinstance(value, datetime):
                        processed_record[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                    elif isinstance(value, date):
                        processed_record[key] = value.strftime('%Y-%m-%d')
                    else:
                        processed_record[key] = value
                if processed_record:
                    result.append(processed_record)
            field_dict = {}
            field_dict[f"{submodel_name}"] = result
            array_items.append(field_dict)

        for key, value in record_values.items():
            processed_record = {}
            field_dict = {}

            if isinstance(value, bytes):
                continue
            elif hasattr(value, '__html__'):
                field_dict[f"{model_name}_{key}"] = str(value)
                markup_items.append(field_dict)
            elif isinstance(value, list) and value and http.request.env[model_name]._fields[key].type == 'one2many':
                related_model = http.request.env[model_name]._fields[key].comodel_name
                related_values = get_related_values(related_model, value)
            elif isinstance(value, tuple) and len(value) == 2:
                processed_record[f"{model_name}_{key}"] = value[1]
            elif isinstance(value, datetime):
                processed_record[f"{model_name}_{key}"] = value.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(value, date):
                processed_record[f"{model_name}_{key}"] = value.strftime('%Y-%m-%d')
            else:
                processed_record[f"{model_name}_{key}"] = value
            
            if processed_record:
                non_array_items.append(processed_record)

        url = config_utils.get_odoo_url(http.request.env) + "onlyoffice/template/download/" + template_attachment_id
        url_with_params = f"{url}?oo_security_token={oo_security_token}"
        
        def format_value_for_json(value):
            if isinstance(value, bool):
                return str(value).lower()
            elif value is None:
                return 'null'
            elif isinstance(value, (int, float)):
                return str(value)
            return value

        formatted_non_array_items = {}
        for d in non_array_items:
            for key, value in d.items():
                formatted_non_array_items[key] = format_value_for_json(value)

        json_non_array_items = json.dumps(formatted_non_array_items, ensure_ascii=False)
        json_array_items = json.dumps(array_items, ensure_ascii=False)

        file_content = f"""
        builder.OpenFile("{url_with_params}");
        var oDocument = Api.GetDocument();
        
        var array_data = {json_array_items};
        var data = {json_non_array_items};

        var aForms = oDocument.GetAllForms();
        aForms.forEach(form => {{
            if (form.GetFormType() == "textForm") {{
                if (data[form.GetFormKey()]) {{
                    form.SetText(String(data[form.GetFormKey()]));
                }}
            }}
            if (form.GetFormType() == "checkBoxForm") {{
                var value = data[form.GetFormKey()];
                if (value) {{
                    try {{
                        var parsedValue = JSON.parse(value);
                        form.SetChecked(parsedValue);
                    }} catch (_e) {{
                        form.SetChecked(value);
                    }}
                }}
            }}
        }});

        function findRecordsByModel(key) {{
            for (let i = 0; i < array_data.length; i++) {{
                if (array_data[i][key]) return array_data[i][key];
            }}
            return [];
        }}

        var oTables = oDocument.GetAllTables();

        oTables.forEach(oTable => {{
            var rows = oTable.GetRowsCount();
            for (let row = 0; row < rows; row++) {{
                var oTableRow = oTable.GetRow(row);
                var nCellsCount = oTableRow.GetCellsCount();
                for (let col = 0; col < nCellsCount; col++) {{
                    var oCell = oTable.GetCell(row, col);
                    var oCellContent = oCell.GetContent();
                    var oCellElementsCount = oCellContent.GetElementsCount();

                    //enum of paragraphs inside the cell
                    for (let cellElement = 0; cellElement < oCellElementsCount; cellElement++) {{
                        var oCellElement = oCellContent.GetElement(cellElement);
                        if (oCellElement.GetClassType() ===  "paragraph") {{
                            var oParagraphElementsCount = oCellElement.GetElementsCount();

                            //enum paragraph elements inside a cell
                            for (let paragraphElement = 0; paragraphElement < oParagraphElementsCount; paragraphElement++) {{
                                var oParagraphElement = oCellElement.GetElement(paragraphElement);

                                //work with form
                                if (oParagraphElement.GetClassType() === "form") {{
                                    var oFormElement = oParagraphElement;
                                    var oFormElementKey = oFormElement.GetFormKey();
                                    
                                    var modelKey = oFormElementKey.split("_");
                                    var modelName = modelKey.shift();
                                    modelKey = modelKey.join("_"); 

                                    var records = findRecordsByModel(modelName);
                                    if (records && oFormElement.GetFormType() == "textForm") {{
                                        if (records[0]) {{
                                            var text = records[0][modelKey];
                                            if (text) oFormElement.SetText(String(text));
                                        }}
                                        
                                        if (records.length > 1) {{
                                            for (let record = 1; record < records.length; record++) {{
                                                var oCurrentCell = oTable.GetCell(row + record, col);
                                                if (oCurrentCell == null) {{
                                                    oTable.AddRow(oTable.GetCell(row + record - 1, col), false);
                                                    oCurrentCell = oTable.GetCell(row + record, col);
                                                }}
                                                if (oCurrentCell) {{
                                                    var text = ""
                                                    if (records[record]) {{
                                                        if (records[record][modelKey]) text = records[record][modelKey];
                                                    }}
                                                    var oParagraph = oCurrentCell.GetContent().GetElement(0);
                                                    oParagraph.AddText(String(text));
                                                }}
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }});
        
        Api.Save();
        builder.SaveFile("docxf", "output.docx");
        builder.CloseFile();
        """
        
        #with file_open('onlyoffice_template/static/test.docbuilder', "r") as f:
        #    test = f.read()

        headers = {
            'Content-Disposition': 'attachment; filename="fillform.docbuilder"',
            'Content-Type': 'text/plain',
        }
        return request.make_response(file_content, headers)
    
    @http.route("/onlyoffice/template/download/<int:template_attachment_id>", auth="public")
    def download_docxf(self, template_attachment_id, oo_security_token=None):
        attachment = request.env['ir.attachment'].sudo().browse(template_attachment_id)
        
        if attachment:
            file_content = base64.b64decode(attachment.datas)
            headers = {
                'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'Content-Disposition': 'attachment; filename="form.docxf"',
            }
            return request.make_response(file_content, headers)
        else:
            return request.not_found()