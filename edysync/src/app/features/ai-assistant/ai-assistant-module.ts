// DCE — Diego Centeno Estuvo Acá
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../shared/shared-module';
import { AiAssistantChat } from './pages/chat/chat';
import { AiAssistantRoutingModule } from './ai-assistant-routing-module';

@NgModule({
  declarations: [
    AiAssistantChat,
  ],
  imports: [
    CommonModule,
    FormsModule,
    SharedModule,
    AiAssistantRoutingModule,
  ],
})
export class AiAssistantModule { }
