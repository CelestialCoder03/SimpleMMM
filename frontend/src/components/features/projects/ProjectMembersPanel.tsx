import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectMembersApi } from '@/api/services';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { UserPlus, Trash2, Crown, Edit3, Eye, Loader2 } from 'lucide-react';
import type { ProjectRole } from '@/types';

interface ProjectMembersPanelProps {
  projectId: string;
  isOwner: boolean;
}

const roleIcons = {
  owner: Crown,
  editor: Edit3,
  viewer: Eye,
};

const roleColors = {
  owner: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  editor: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  viewer: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
};

export function ProjectMembersPanel({ projectId, isOwner }: ProjectMembersPanelProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberRole, setNewMemberRole] = useState<ProjectRole>('viewer');

  const { data: membersData, isLoading } = useQuery({
    queryKey: ['project-members', projectId],
    queryFn: () => projectMembersApi.list(projectId),
  });

  const addMemberMutation = useMutation({
    mutationFn: (data: { email: string; role: ProjectRole }) =>
      projectMembersApi.add(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-members', projectId] });
      setIsAddDialogOpen(false);
      setNewMemberEmail('');
      setNewMemberRole('viewer');
    },
  });

  const updateMemberMutation = useMutation({
    mutationFn: ({ memberId, role }: { memberId: string; role: ProjectRole }) =>
      projectMembersApi.update(projectId, memberId, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-members', projectId] });
    },
  });

  const removeMemberMutation = useMutation({
    mutationFn: (memberId: string) => projectMembersApi.remove(projectId, memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-members', projectId] });
    },
  });

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const handleAddMember = () => {
    if (newMemberEmail.trim()) {
      addMemberMutation.mutate({ email: newMemberEmail.trim(), role: newMemberRole });
    }
  };

  const members = membersData?.members || [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-lg">{t('projects.teamMembers')}</CardTitle>
          <CardDescription>
            {t('projects.manageAccess')}
          </CardDescription>
        </div>
        {isOwner && (
          <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <UserPlus className="mr-2 h-4 w-4" />
                {t('projects.addMember')}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t('projects.addTeamMember')}</DialogTitle>
                <DialogDescription>
                  {t('projects.inviteByEmail')}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="email">{t('projects.emailAddress')}</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder={t('projects.emailPlaceholder')}
                    value={newMemberEmail}
                    onChange={(e) => setNewMemberEmail(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="role">{t('projects.role')}</Label>
                  <Select
                    value={newMemberRole}
                    onValueChange={(value: ProjectRole) => setNewMemberRole(value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="editor">
                        <div className="flex items-center gap-2">
                          <Edit3 className="h-4 w-4" />
                          <span>{t('projects.editor')}</span>
                          <span className="text-xs text-muted-foreground">
                            - {t('projects.editorDesc')}
                          </span>
                        </div>
                      </SelectItem>
                      <SelectItem value="viewer">
                        <div className="flex items-center gap-2">
                          <Eye className="h-4 w-4" />
                          <span>{t('projects.viewer')}</span>
                          <span className="text-xs text-muted-foreground">
                            - {t('projects.viewerDesc')}
                          </span>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {addMemberMutation.isError && (
                  <p className="text-sm text-destructive">
                    {(addMemberMutation.error as Error)?.message || t('projects.addMemberFailed')}
                  </p>
                )}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>
                  {t('common.cancel')}
                </Button>
                <Button
                  onClick={handleAddMember}
                  disabled={!newMemberEmail.trim() || addMemberMutation.isPending}
                >
                  {addMemberMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {t('projects.addMember')}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-3">
            {members.map((member) => {
              const RoleIcon = roleIcons[member.role];
              const isOwnerMember = member.role === 'owner';
              
              return (
                <div
                  key={member.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex items-center gap-3">
                    <Avatar className="h-10 w-10">
                      <AvatarFallback className="bg-primary/10 text-primary">
                        {getInitials(member.user.full_name)}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <p className="font-medium">{member.user.full_name}</p>
                      <p className="text-sm text-muted-foreground">{member.user.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {isOwner && !isOwnerMember ? (
                      <>
                        <Select
                          value={member.role}
                          onValueChange={(value: ProjectRole) =>
                            updateMemberMutation.mutate({ memberId: member.id, role: value })
                          }
                        >
                          <SelectTrigger className="w-28">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="editor">{t('projects.editor')}</SelectItem>
                            <SelectItem value="viewer">{t('projects.viewer')}</SelectItem>
                          </SelectContent>
                        </Select>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:bg-destructive/10"
                          onClick={() => removeMemberMutation.mutate(member.id)}
                          disabled={removeMemberMutation.isPending}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </>
                    ) : (
                      <Badge className={roleColors[member.role]}>
                        <RoleIcon className="mr-1 h-3 w-3" />
                        {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                      </Badge>
                    )}
                  </div>
                </div>
              );
            })}
            {members.length === 0 && (
              <p className="py-4 text-center text-sm text-muted-foreground">
                {t('projects.noMembers')}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
