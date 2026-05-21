// DCE — Diego Centeno Estuvo Acá
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AiAssistantChat } from './pages/chat/chat';

const routes: Routes = [
  { path: '', component: AiAssistantChat, pathMatch: 'full' },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class AiAssistantRoutingModule { }
