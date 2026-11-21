import type { ReactNode } from 'react';
import { KpiWidget, MinimapWidget, ProgramsWidget, RankWidget, SnapshotWidget, SnapWidget } from './districtWidgets';
import { CrimeWidget, HousingWidget, RepsWidget, SchoolsWidget, TrendsWidget } from './contextWidgets';
import { AnswerWidget, AskWidget, CalendarWidget, ChatsWidget, HolidaysWidget, NotesWidget, UsageWidget } from './toolWidgets';
import type { WidgetProps } from './types';

export function renderWidget(p: WidgetProps): ReactNode {
  const t = p.w.type;
  switch (t) {
    case 'snapshot': return <SnapshotWidget {...p} />;
    case 'kpi': return <KpiWidget {...p} />;
    case 'rank': return <RankWidget {...p} />;
    case 'minimap': return <MinimapWidget {...p} />;
    case 'snap': return <SnapWidget {...p} />;
    case 'programs': return <ProgramsWidget {...p} />;
    case 'trends': return <TrendsWidget {...p} />;
    case 'crime': return <CrimeWidget {...p} />;
    case 'schools': return <SchoolsWidget {...p} />;
    case 'housing': return <HousingWidget {...p} />;
    case 'reps': return <RepsWidget {...p} />;
    case 'ask': return <AskWidget {...p} />;
    case 'chats': return <ChatsWidget {...p} />;
    case 'answer': return <AnswerWidget {...p} />;
    case 'holidays': return <HolidaysWidget {...p} />;
    case 'calendar': return <CalendarWidget {...p} />;
    case 'notes': return <NotesWidget {...p} />;
    case 'usage': return <UsageWidget {...p} />;
    default: { const never: never = t; return never; }
  }
}
