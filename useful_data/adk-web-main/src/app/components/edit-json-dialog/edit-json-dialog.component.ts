/**
 * @license
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import {Component, Inject, OnInit, ViewChild} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';

import {JsonEditorComponent} from '../json-editor/json-editor.component';

export interface EditJsonData {
  dialogHeader: string;
  functionName?: string;
  jsonContent?: any;
}

@Component({
  selector: 'app-edit-json-dialog',
  templateUrl: './edit-json-dialog.component.html',
  styleUrls: ['./edit-json-dialog.component.scss'],
  standalone: false,
})
export class EditJsonDialogComponent implements OnInit {
  @ViewChild(JsonEditorComponent) jsonEditorComponent!: JsonEditorComponent;
  protected jsonString = '';
  protected functionName = '';

  constructor(
      public dialogRef: MatDialogRef<EditJsonDialogComponent>,
      @Inject(MAT_DIALOG_DATA) public data: EditJsonData) {
    this.jsonString = JSON.stringify(data.jsonContent, null, 2);
    this.functionName = data.functionName || '';
  }

  ngOnInit(): void {}

  onSave(): void {
    try {
      this.jsonString = this.jsonEditorComponent.getJsonString();
      const parsedArgs = JSON.parse(this.jsonString);
      this.dialogRef.close(parsedArgs);
    } catch (e) {
      alert('Invalid JSON: ' + e);
    }
  }

  onCancel(): void {
    this.dialogRef.close(null);
  }
}
